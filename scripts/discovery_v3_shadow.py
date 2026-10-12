"""HD Careers V3 employer-first discovery shadow probe: read-only, evidence-first."""
from __future__ import annotations
import argparse
import html
import json
import re
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "HDCareersShadowResearch/1.0"
HOSTS = {
    "EY": {"host": "careers.ey.com", "listing": "https://careers.ey.com/ey/search/"},
    "Deloitte South Asia": {"host": "southasiacareers.deloitte.com", "listing": "https://southasiacareers.deloitte.com/search/"},
    "HCLTech": {"host": "careers.hcltech.com", "listing": "https://careers.hcltech.com/go/India/9553955/"}
}
CLOSURE = re.compile(r"(?:this job (?:is )?no longer (?:available|accepting applications)|job has been (?:closed|filled)|position has been filled|applications are closed)", re.I)
APPLY = re.compile(r"\\b(?:apply now|apply for this job|apply to this job|apply now »)\\b", re.I)
REQUISITION = re.compile(r"\\brequisition\\s*(?:id)?\\s*[:#–-]?\\s*([0-9]{5,9})", re.I)

class ListingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.visible = []
        self.href = ""
        self.link_text = ""
        self.in_script = 0
        self.in_anchor = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style"): self.in_script += 1
        if tag == "a":
            self.in_anchor = True
            self.href = a.get("href", "")
            self.link_text = ""

    def handle_data(self, data):
        if not self.in_script: self.visible.append(data)
        if self.in_anchor: self.link_text += data

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.in_script: self.in_script -= 1
        if tag == "a" and self.in_anchor:
            self.links.append((self.href, re.sub(r"\\s+", " ", self.link_text).strip()))
            self.in_anchor = False

def classify_exact(html_text, url, expected_id, expected_role):
    parser = ListingParser()
    parser.feed(html_text)
    text = re.sub(r"\\s+", " ", html.unescape(" ".join(parser.visible))).strip()
    if CLOSURE.search(text):
        return {"state": "unconfirmed", "reason": "Closure words need exact-job and listing corroboration", "evidence": ["closure-text"]}
    role = " ".join(re.findall(r"[a-z0-9]+", expected_role.lower()))
    normalized = " ".join(re.findall(r"[a-z0-9]+", text.lower()))
    role_found = bool(role and role in normalized)
    id_found = bool(expected_id and expected_id in text)
    apply_present = bool(APPLY.search(text) or any("apply" in t.lower() and h and not h.startswith("#") for h,t in parser.links))
    evidence = [name for name, ok in (("matching-title", role_found),("matching-requisition", id_found),("apply-control", apply_present)) if ok]
    if all((role_found, id_found, apply_present)):
        return {"state": "live", "reason": "Exact title and requisition plus visible Apply control", "evidence": evidence}
    return {"state": "unconfirmed", "reason": "Job identity or Apply control is insufficient", "evidence": evidence}

def classify_listing_absence(last, current, id):
    """An omitted listing is not proof of expiry if either crawl was partial."""
    if not all(isinstance(x, dict) and x.get("complete") and x.get("status") == "ok" for x in (last, current)):
        return "unconfirmed"
    if last.get("employer") != current.get("employer") or last.get("filter") != current.get("filter"):
        return "unconfirmed"
    if id not in last.get("ids", []):
        return "unconfirmed"
    return "missing_once" if id not in current.get("ids", []) else "live"

def robots_allowed(url):
    u = urlparse(url)
    robots = f"{u.scheme}://{u.netloc}/robots.txt"
    req = Request(robots, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=10) as response:
            if response.status != 200: return False, "robots unavailable"
            rules = response.read(250_000).decode("utf-8", errors="replace")
        parser = RobotFileParser()
        parser.parse(rules.splitlines())
        return parser.can_fetch(USER_AGENT, url), "robots checked"
    except (HTTPError, URLError, TimeoutError, OSError):
        return False, "robots unreadable (fail closed)"

def get_official_page(url, company):
    expected = HOSTS[company]["host"]
    if urlparse(url).scheme != "https" or urlparse(url).hostname != expected:
        return {"status": "blocked", "reason": "Host does not match approved employer"}
    allowed, reason = robots_allowed(url)
    if not allowed: return {"status": "blocked", "reason": reason}
    try:
        with urlopen(Request(url, headers={"User-Agent": USER_AGENT,"Accept":"text/html"}), timeout=12) as response:
            final = response.geturl()
            if urlparse(final).hostname != expected: return {"status": "blocked", "reason": "Cross-host redirect"}
            body = response.read(1_200_000).decode("utf-8", errors="replace")
        return {"status": "ok", "body": body, "finalUrl": final}
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        return {"status": "unconfirmed", "reason": type(exc).__name__ + ": no closing claim"}

def extract_listed_jobs(body, base, host):
    parser = ListingParser()
    parser.feed(body)
    jobs = {}
    for href,title in parser.links:
        url = urljoin(base, href)
        if urlparse(url).hostname != host: continue
        if not re.search(r"/(?:job|jobs)/",urlparse(url).path,re.I): continue
        if not title or len(title)>200: continue
        match = re.search(r"/(\\d{6,12})(?:/|$)", urlparse(url).path)
        if not match: continue
        jobs[match.group(1)]={"title":title,"url":url}
    return jobs

def shadow(seeds, published):
    checked = []
    today = datetime.now(timezone.utc).isoformat()
    known = {str(j.get("apply","")).rstrip("/").lower() for j in published}
    for idx, seed in enumerate(seeds):
        company = seed["company"]
        url = seed["url"]
        test = get_official_page(url, company)
        row = {"company":company,"role":seed["role"],"jobId":seed["jobId"],"apply":url,
               "alreadyPublished":url.rstrip("/").lower() in known,
               "state":"unconfirmed","reason":test.get("reason",""),"evidence":[]}
        if test["status"] == "ok":
            verdict = classify_exact(test["body"], url,seed["jobId"],seed["role"])
            row.update(verdict)
            row["bytesFetched"] = len(test["body"])
        else:
            row["reason"]=test.get("reason","Access unavailable")
        checked.append(row)
        if idx<len(seeds)-1: time.sleep(1)
    return {"runType":"shadow_only","checkedAt":today,"providers":list(HOSTS),
            "newLive":[r for r in checked if r["state"]=="live" and not r["alreadyPublished"]],
            "counts":{"live":sum(r["state"]=="live" for r in checked),
                      "unconfirmed":sum(r["state"]=="unconfirmed" for r in checked),
                      "newLive":sum(r["state"]=="live" and not r["alreadyPublished"] for r in checked)},
            "results":checked,"warning":"No jobs were published, closed or marked expired in shadow mode."}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--seeds", default="data/discovery-v3-seeds.json")
    ap.add_argument("--published",default="data/jobs.json")
    ap.add_argument("--output",default="discovery-v3-shadow-report.json")
    args=ap.parse_args()
    seeds=json.loads((ROOT/args.seeds).read_text())
    published=json.loads((ROOT/args.published).read_text())
    if not isinstance(seeds,list) or not isinstance(published,list): raise SystemExit("Inputs must be arrays")
    for seed in seeds:
        if seed.get("company") not in HOSTS or not re.fullmatch(r"[0-9]{5,12}",str(seed.get("jobId",""))):
            raise SystemExit("Unexpected employer or requisition")
    report=shadow(seeds,published)
    Path(args.output).write_text(json.dumps(report,indent=2)+"\n")
    for r in report["results"]:
        print(f"{r['company']}: {r['state']} | {r['role']} | {r['reason']} | alreadyPublished={r['alreadyPublished']}")
    print(json.dumps(report["counts"]))

if __name__=="__main__": main()
