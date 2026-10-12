"""Extract only employer-authored JobPosting facts; never fabricate missing fields."""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

class StructuredScripts(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.collect = False
        self.parts = []
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        if tag == "script" and "ld+json" in dict(attrs).get("type", "").lower():
            self.collect = True
            self.parts = []

    def handle_data(self, data):
        if self.collect:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.collect:
            self.scripts.append("".join(self.parts))
            self.collect = False
            self.parts = []

class PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.words = []
    def handle_data(self, data):
        if data.strip():
            self.words.append(data.strip())

def clean(value):
    if isinstance(value, list):
        return "; ".join(filter(None, (clean(x) for x in value)))
    if isinstance(value, dict):
        return clean(value.get("value") or value.get("name") or "")
    if value is None:
        return ""
    parser = PlainText()
    parser.feed(unescape(str(value)))
    return " ".join(" ".join(parser.words).split())[:12000]

def nodes(data):
    if isinstance(data, list):
        for value in data:
            yield from nodes(value)
    elif isinstance(data, dict):
        types = data.get("@type", [])
        if isinstance(types, str):
            types = [types]
        if "JobPosting" in types:
            yield data
        graph = data.get("@graph")
        if graph is not None:
            yield from nodes(graph)

def parse_until(value, now):
    if not value:
        return "unspecified"
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                # Date-only validThrough means the entire calendar day.
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                    return "past" if parsed.date() < now.date() else "future"
                return "unconfirmed"
            return "past" if parsed.astimezone(timezone.utc) < now else "future"
        except ValueError:
            pass
    return "unconfirmed"

def extract_facts(body, exact_url, employer, expected_title, now=None):
    now = now or datetime.now(timezone.utc)
    assert urlsplit(exact_url).scheme == "https"
    scripts = StructuredScripts()
    scripts.feed(body)
    matched = []
    for script in scripts.scripts:
        try:
            candidates = list(nodes(json.loads(script)))
        except (ValueError,TypeError):
            continue
        for post in candidates:
            org = post.get("hiringOrganization") or {}
            organization = clean(org.get("name") if isinstance(org, dict) else org)
            if not organization or employer.casefold() not in organization.casefold():
                continue
            posted_url = post.get("url")
            if posted_url:
                resolved = urljoin(exact_url,posted_url)
                if urlsplit(resolved).hostname != urlsplit(exact_url).hostname or \
                        urlsplit(resolved).path.rstrip("/") != urlsplit(exact_url).path.rstrip("/"):
                    continue
            title = clean(post.get("title"))
            if not title or " ".join(re.findall(r"\w+",title.lower())) != \
                    " ".join(re.findall(r"\w+",expected_title.lower())):
                continue
            expiry = parse_until(post.get("validThrough"),now)
            if expiry == "past":
                return {"status":"unconfirmed","reason":"Structured application deadline passed; check employer listing",
                        "missing":[],"facts":{}}
            description = clean(post.get("description"))
            qualifications = clean(post.get("qualifications") or post.get("educationRequirements"))
            duties = clean(post.get("responsibilities"))
            location = post.get("jobLocation") or {}
            if isinstance(location,list):
                location = location[0] if location else {}
            address = location.get("address",{}) if isinstance(location,dict) else {}
            if not isinstance(address,dict):
                address = {}
            country = address.get("addressCountry")
            if isinstance(country,dict):
                country = country.get("name")
            if country and str(country).lower() not in ("in","india"):
                continue
            facts = {"company": employer, "role": title, "desc": description,
                     "elig": qualifications, "resp": [duties] if duties else [],
                     "loc": ", ".join(str(x) for x in (
                         address.get("addressLocality"), address.get("addressRegion"), country
                     ) if x),
                     "sourceName": employer+" official careers",
                     "apply": exact_url,
                     "datePosted": post.get("datePosted") or "Not specified",
                     "skills": [clean(post.get("skills"))] if post.get("skills") else [],
                     "closingDate": post.get("validThrough") or "Not specified"}
            missing = [key for key in ("desc","elig","loc") if not facts[key]]
            if not facts["resp"]:
                missing.append("resp")
            matched.append({"status":"content_ready" if not missing else "incomplete",
                            "reason":"Employer JobPosting structured facts",
                            "facts":facts,"missing":missing,
                            "sourceEvidence":["employer-identity","matching-title",
                                              "official-job-url","JobPosting-JSONLD"]})
    if matched:
        return sorted(matched,key=lambda x:len(x["missing"]))[0]
    return {"status":"unconfirmed","reason":"No exact official JobPosting structured data found",
            "facts":{},"missing":["source_details"]}


def main():
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser()
    parser.add_argument("--html", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--output", default="v3-source-draft.json")
    args=parser.parse_args()
    result=extract_facts(Path(args.html).read_text(),args.url,args.company,args.title)
    Path(args.output).write_text(json.dumps(result,indent=2)+"\n")
    print(result["status"],result["missing"])


if __name__=="__main__":
    main()
