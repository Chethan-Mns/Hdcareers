"""Read-only fingerprinting of the remaining eight official employer careers sites.

Identifies the next adapter to build. It never discovers/publishes a job or
declares vacancies Live/Expired.
"""
from __future__ import annotations
import argparse
import json
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser
from discovery_v3_source_registry import EMPLOYERS, fingerprint

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "HDCareersShadowResearch/1.0"

class LinkCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.current = {"href":dict(attrs).get("href",""),"text":[]}

    def handle_data(self, text):
        if self.current is not None:
            self.current["text"].append(text)

    def handle_endtag(self, tag):
        if tag == "a" and self.current is not None:
            item = self.current
            item["text"] = " ".join(" ".join(item["text"]).split())[:110]
            self.links.append(item)
            self.current = None

def employer_links(html, source_url, allowed_host):
    parser = LinkCollector()
    parser.feed(html)
    found, seen = [], set()
    for item in parser.links:
        target = urljoin(source_url, item["href"])
        host = urlsplit(target).hostname
        if host not in {allowed_host,allowed_host.removeprefix("www."),
                        "www."+allowed_host.removeprefix("www.")}:
            continue
        if not target.startswith("https://"):
            continue
        if not any(term in (target+" "+item["text"]).lower()
                   for term in ("job","career","vacanc","search","apply","opportunit")):
            continue
        if target in seen:
            continue
        seen.add(target)
        found.append({"text":item["text"],"url":target})
    return found[:12]

def robots_ok(url, timeout=10):
    parts=urlsplit(url)
    robots="https://"+parts.netloc+"/robots.txt"
    try:
        with urlopen(Request(robots,headers={"User-Agent":USER_AGENT}),timeout=timeout) as response:
            if response.status != 200:
                return False,"robots not confirmed"
            parser=RobotFileParser()
            parser.parse(response.read(200_000).decode("utf-8","replace").splitlines())
            return parser.can_fetch(USER_AGENT,url),"robots checked"
    except (HTTPError,URLError,OSError,TimeoutError):
        return False,"robots unavailable"

def probe(source, fetch=None):
    # The optional fetch function only supports offline fixture tests.
    record={"company":source.name,"configuredHost":source.host,
            "portal":source.url,"stage":source.stage,
            "status":"unconfirmed","family":"unconfirmed",
            "jobCount":None,"canPublish":False,"canExpire":False,
            "evidence":[],"sampleLinks":[]}
    if source.stage != "probe_only":
        record["reason"]="Not a new-employer probe"
        return record
    if fetch is None:
        allowed,why=robots_ok(source.url)
        if not allowed:
            record["status"]="blocked"
            record["reason"]=why
            return record
        try:
            req=Request(source.url,headers={"User-Agent":USER_AGENT,
                       "Accept":"text/html,application/xhtml+xml"})
            with urlopen(req,timeout=12) as response:
                final=response.geturl()
                body=response.read(800_000).decode("utf-8","replace")
                status=response.status
                ctype=response.headers.get("Content-Type","text/html")
        except (HTTPError,URLError,OSError,TimeoutError) as exc:
            record["reason"]=type(exc).__name__+"; never implies job closure"
            return record
    else:
        result=fetch(source)
        final=result.get("url",source.url)
        status=result.get("status",0)
        body=result.get("body","")
        ctype=result.get("contentType","text/html")
    redirected=urlsplit(final).hostname not in {source.host,source.host.removeprefix("www."),
                                 "www."+source.host.removeprefix("www.")}
    if redirected:
        record.update(status="needs_manual_mapping",
                      reason="Redirected to a different host: verify employer control before following")
        return record
    if status!=200:
        record["reason"]="Employer page did not return HTTP 200"
        return record
    family=fingerprint(body,ctype)
    links=employer_links(body,final,source.host)
    record.update(status="scouted",family=family,
                  reason="Career portal reached; full-list extraction not yet validated",
                  evidence=["official-page-200","allowed-first-party-host","page-fingerprint"],
                  sampleLinks=links)
    return record

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",default="discovery-v3-expansion-probe.json")
    ap.add_argument("--sleep",type=float,default=0.6)
    args=ap.parse_args()
    if args.sleep < 0:
        ap.error("Sleep must be nonnegative")
    selected=[x for x in EMPLOYERS if x.stage=="probe_only"]
    results=[]
    for index,source in enumerate(selected):
        result=probe(source)
        print(source.name,result["status"],result.get("family"),
              result.get("reason",""))
        results.append(result)
        if index!=len(selected)-1 and args.sleep:
            time.sleep(args.sleep)
    payload={"mode":"read_only_portal_fingerprint",
             "checkedAt":datetime.now(timezone.utc).isoformat(),
             "companies":results,
             "summary":{"scouted":sum(x["status"]=="scouted" for x in results),
                        "blocked":sum(x["status"]=="blocked" for x in results),
                        "needsMapping":sum(x["status"]=="needs_manual_mapping" for x in results)},
             "automaticPublishingEnabled":False,
             "warning":"An HTTP 200 portal is not a verified live job. No jobs modified or published."}
    Path(args.output).write_text(json.dumps(payload,indent=2)+"\n")
    print("Only source-adapter diagnostics written; no publication or expiry actions.")

if __name__=="__main__":
    main()
