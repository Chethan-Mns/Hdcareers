"""Read-only V3 listings: conservative pagination, deduplication and source evidence.

A partial/blocked crawl NEVER means a vacancy has expired. This script does not
publish jobs or write to data/jobs.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser


ROOT = Path(__file__).resolve().parents[1]
AGENT = "HDCareersShadowResearch/1.0"
PAGE_SIZE = 25
DEFAULTS = {
    "EY": {"host": "careers.ey.com", "path": "/ey/search/",
           "mode": "successfactors"},
    "Deloitte South Asia": {"host": "southasiacareers.deloitte.com",
           "path": "/go/Deloitte-India/718244/", "mode": "successfactors"},
    "HCLTech": {"host": "careers.hcltech.com",
           "path": "/go/India/9553955/", "mode": "hcl"},
    "Wipro": {"host": "careers.wipro.com",
           "path": "/viewalljobs/", "mode": "successfactors", "page_size": 50},
}
def page_size(company):
    return int(DEFAULTS[company].get("page_size", PAGE_SIZE))


RESULTS = re.compile(
    r"Results\s+([\d,]+)\s*[–-]\s*([\d,]+)\s+of\s+([\d,]+)"
    r"\s+Page\s+([\d,]+)\s+of\s+([\d,]+)", re.I
)


def normalized_url(url):
    parsed = urlsplit(url)
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path,
                       "", ""))


def job_key(employer, url):
    return hashlib.sha256((employer + "\n" + normalized_url(url)).encode()).hexdigest()[:24]


class ListingHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.visible = []
        self._current = None
        self._script = 0
        self.canonical = ""
        self._row_text = None
        self._row_links = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style"):
            self._script += 1
        if tag == "tr":
            self._row_text = []
            self._row_links = len(self.links)
        if tag == "link" and "canonical" in str(attrs.get("rel", "")).lower():
            self.canonical = attrs.get("href", "")
        if tag == "a":
            self._current = {"url": attrs.get("href", ""), "text": []}

    def handle_data(self, value):
        if not self._script:
            self.visible.append(value)
            if self._row_text is not None:
                self._row_text.append(value)
        if self._current is not None:
            self._current["text"].append(value)

    def handle_endtag(self, tag):
        if tag == "tr" and self._row_text is not None:
            text = " ".join(" ".join(self._row_text).split())
            for link in self.links[self._row_links:]:
                link["rowText"] = text
            self._row_text = None
            self._row_links = None
        if tag in ("script", "style") and self._script:
            self._script -= 1
        if tag == "a" and self._current is not None:
            row = self._current
            row["text"] = " ".join(" ".join(row["text"]).split())
            self.links.append(row)
            self._current = None


def job_from_link(company, href, title, source):
    if not href or not title or len(title) > 220:
        return None
    url = urljoin(source, href)
    parsed = urlsplit(url)
    conf = DEFAULTS[company]
    if parsed.scheme != "https" or parsed.hostname != conf["host"]:
        return None
    path = parsed.path
    if not re.search(r"/job/", path, re.I):
        return None
    # All three portals use job-specific paths ending in numeric identifiers.
    match = re.search(r"/(\d{5,12})(?:/|$)", path)
    if not match:
        match = re.search(r"/(\d{5,12})-[a-z]{2}_[a-z]{2}/?$", path, re.I)
    if not match:
        return None
    requisition_url_id = match.group(1)
    return {
        "id": job_key(company, url),
        "company": company,
        "title": title,
        "jobUrl": normalized_url(url),
        "listingUrlId": requisition_url_id,
        "status": "listed_unverified",
        "evidence": ["official-listing-link"],
    }


def parse_page(company, html, source, expected_page=0):
    parser = ListingHTML()
    parser.feed(html)
    content = " ".join(" ".join(parser.visible).split())
    m = RESULTS.search(content)
    if not m:
        return {"valid": False, "reason": "Total results and full-page bounds unavailable",
                "jobs": [], "total": None, "pages": None}
    start, end, total, page_number, pages = [int(n.replace(",", "")) for n in m.groups()]
    size = page_size(company)
    expected_start = expected_page * size + 1
    expected_end = min((expected_page + 1) * size, total)
    if (start, end, page_number) != (expected_start, expected_end, expected_page + 1):
        return {"valid": False, "reason": "Pagination range or page number mismatch",
                "jobs": [], "total": total, "pages": pages}
    if total < 0 or pages != (total + size - 1) // size:
        return {"valid": False, "reason": "Reported total and page count disagree",
                "jobs": [], "total": total, "pages": pages}
    unique = {}
    eligible_links = []
    for link in parser.links:
        # SuccessFactors includes promotional and campaign job links outside
        # the actual result table. Only counted table rows belong to pagination.
        if DEFAULTS[company]["mode"] == "successfactors" and "rowText" not in link:
            continue
        job = job_from_link(company, link["url"], link["text"], source)
        if job:
            eligible_links.append(link)
            row = link.get("rowText", "")
            job["locationEvidence"] = row[-220:] if row else ""
            # EY and Wipro are global boards: require positive India evidence
            # in the result row rather than inferring from the company name.
            job["country"] = "IN" if re.search(r"(?:,\s*IN\b|\bIndia\b)", row, re.I) else "unconfirmed"
            if company not in ("EY", "Wipro"):
                job["country"] = "IN"
            unique[job["id"]] = job
    if len(unique) != end - start + 1:
        paths = [urlsplit(urljoin(source, l["url"])).path[:120] for l in eligible_links[:3]]
        return {"valid": False,
                "reason": f"Job-row mismatch: expected {end-start+1}, got {len(unique)} (links {len(eligible_links)}); samples {paths}",
                "jobs": list(unique.values()), "total": total, "pages": pages}
    return {"valid": True, "reason": "Exact listing count and page bounds match",
            "jobs": list(unique.values()), "total": total, "pages": pages}


def verify_exact_listing_job(html_body, job):
    """For SuccessFactors, URL listing ID differs from the visible requisition ID.

    Require three separate signals: exact canonical, title visible, and an
    actual Apply control on the exact employer page. Never trust status=200.
    """
    parser = ListingHTML()
    parser.feed(html_body)
    canonical = normalized_url(urljoin(job["jobUrl"], parser.canonical)) if parser.canonical else ""
    if canonical != job["jobUrl"]:
        return {"state":"unconfirmed", "reason":"Canonical URL did not match exact official listing",
                "evidence":[]}
    if re.search(r"(?:this (?:job|position) (?:is )?no longer available|"+
                 r"(?:applications? (?:are |is )?closed)|no longer accepting applications|"+
                 r"(?:position|job) has been filled)", " ".join(parser.visible), re.I):
        return {"state":"unconfirmed",
                "reason":"Employer page contains a closure notice; independent confirmation required",
                "evidence":["possible-closure-text"]}
    normalized_text = " ".join(re.findall(r"[a-z0-9]+",
        " ".join(parser.visible).lower()))
    expected_title = " ".join(re.findall(r"[a-z0-9]+", job["title"].lower()))
    title_match = bool(expected_title and expected_title in normalized_text)
    has_apply = any("apply" in link["text"].casefold() and
                    link["url"].strip() and link["url"].strip() not in ("#", "javascript:void(0)")
                    for link in parser.links)
    # Some SuccessFactors Apply buttons are form actions instead of links.
    has_apply = has_apply or bool(re.search(
        r"<(?:button|input)\b[^>]*(?:apply now|apply for this job)",
        html_body, re.I))
    evidence = [k for k,flag in (("canonical-match", bool(canonical)),
                ("title-match", title_match), ("apply-control", has_apply)) if flag]
    if title_match and has_apply:
        return {"state":"live","reason":"Exact canonical job, title and Apply control confirmed",
                "evidence":evidence}
    return {"state":"unconfirmed","reason":"Title or application control not confirmed",
            "evidence":evidence}


def listing_url(company, index):
    config = DEFAULTS[company]
    base = "https://" + config["host"] + config["path"]
    if config["mode"] == "successfactors":
        if company == "Wipro":
            params = {"locale": "en_US"}
            if index > 0:
                base = base.rstrip("/") + "/" + str(index * page_size(company)) + "/"
        else:
            params = {"q": "", "sortColumn": "referencedate", "sortDirection": "desc"}
            if company == "EY":
                params["startrow"] = index * page_size(company)
            elif index > 0:
                base = base.rstrip("/") + "/" + str(index * page_size(company)) + "/"
    else:
        # HCL India career page can expose a separate dynamically loaded listing.
        # Its missing count is never treated as complete without a trusted total.
        params = {"page": index}
    return base + "?" + urlencode(params)


class AllowedHostFetcher:
    def __init__(self, timeout=12):
        self.timeout = timeout
        self.rules = {}

    def _load_robots(self, host):
        if host not in self.rules:
            url = "https://" + host + "/robots.txt"
            try:
                with urlopen(Request(url, headers={"User-Agent": AGENT}),
                             timeout=self.timeout) as response:
                    if response.status != 200:
                        self.rules[host] = None
                    else:
                        rules = RobotFileParser()
                        rules.parse(response.read(200_000).decode("utf-8", "replace").splitlines())
                        self.rules[host] = rules
            except (HTTPError, URLError, OSError, TimeoutError):
                self.rules[host] = None
        return self.rules[host]

    def get(self, url, company):
        parsed = urlsplit(url)
        host = DEFAULTS[company]["host"]
        if parsed.scheme != "https" or parsed.hostname != host:
            return {"status": "blocked", "reason": "Unapproved URL or employer hostname"}
        rules = self._load_robots(host)
        if not rules or not rules.can_fetch(AGENT, url):
            return {"status": "blocked", "reason": "robots.txt unavailable or disallows route"}
        try:
            request = Request(url, headers={"User-Agent": AGENT,
                "Accept": "text/html,application/xhtml+xml"})
            with urlopen(request, timeout=self.timeout) as response:
                final = response.geturl()
                if urlsplit(final).hostname != host or response.status != 200:
                    return {"status": "unconfirmed", "reason": "Redirected or non-200 employer page"}
                body = response.read(2_000_000).decode("utf-8", "replace")
            return {"status": "ok", "body": body, "url": final}
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            return {"status": "unconfirmed", "reason": type(error).__name__}


def scan_employer(company, fetcher, max_pages=2, pause=0.5):
    if company not in DEFAULTS:
        raise ValueError("Unsupported employer")
    rows, seen = [], set()
    total = None
    expected_pages = None
    problems = []
    max_pages = max(1, min(int(max_pages), 400))
    for index in range(max_pages):
        url = listing_url(company, index)
        response = fetcher.get(url, company)
        if response["status"] != "ok":
            problems.append({"page": index + 1, "reason": response["reason"]})
            break
        page = parse_page(company, response["body"], url, index)
        if not page["valid"]:
            problems.append({"page": index + 1, "reason": page["reason"]})
            break
        if total is None:
            total, expected_pages = page["total"], page["pages"]
        elif total != page["total"] or expected_pages != page["pages"]:
            # Keep discovering visible jobs, but NEVER treat this snapshot as
            # complete or use absences from it to close published listings.
            problems.append({"page": index + 1, "reason": f"Listing total changed during crawl: {total} -> {page['total']}"})
        page_ids = {r["id"] for r in page["jobs"]}
        if page_ids & seen:
            problems.append({"page": index + 1, "reason": "Overlap across result pages"})
            break
        seen |= page_ids
        rows.extend(page["jobs"])
        if index + 1 == expected_pages:
            break
        if index + 1 < max_pages and pause:
            time.sleep(pause)
    complete = (not problems and expected_pages is not None
                and len(rows) == total and
                len(rows) > 0)
    return {
        "employer": company,
        "filter": "official-global" if company == "EY" else "India",
        "status": "ok" if complete else "partial",
        "complete": complete,
        "totalReported": total,
        "pagesReported": expected_pages,
        "pagesRead": (len(rows) + page_size(company) - 1) // page_size(company),
        "jobs": rows,
        "ids": [x["id"] for x in rows],
        "problems": problems or ([] if complete else ["Page limit reached before complete pagination"]),
        "checkedAt": datetime.now(timezone.utc).isoformat(),
    }


def consecutive_absence(history, company, job_id):
    """Only successful *complete* scans of the exact same scope count."""
    chain = [s for s in history if s.get("employer") == company]
    if len(chain) < 3:
        return "unconfirmed"
    newest, previous, older = chain[-1], chain[-2], chain[-3]
    if not all(s.get("complete") and s.get("status") == "ok" for s in (newest, previous, older)):
        return "unconfirmed"
    if len({s.get("filter") for s in (newest, previous, older)}) != 1:
        return "unconfirmed"
    if (job_id in older.get("ids", [])
        and job_id not in previous.get("ids", [])
        and job_id not in newest.get("ids", [])):
        return "missing_twice_needs_closure_evidence"
    return "unconfirmed"


def process(scans, published, fetcher, verify_new=3, pause=0.5):
    known_urls = {normalized_url(x.get("apply", "")) for x in published if x.get("apply")}
    known_ids = {(str(x.get("company","")).casefold(), str(x.get("jobId","")))
                 for x in published if x.get("jobId")}
    new, checked = [], []
    for scan in scans:
        for row in scan["jobs"]:
            row["alreadyPublished"] = (row["jobUrl"] in known_urls or
                (row["company"].casefold(), row["listingUrlId"]) in known_ids)
            if not row["alreadyPublished"] and row["country"] == "IN":
                new.append(row)
    for row in new[:verify_new]:
        company = row["company"]
        response = fetcher.get(row["jobUrl"], company)
        verdict = {"state": "unconfirmed", "reason": response.get("reason","")}
        if response["status"] == "ok":
            verdict = verify_exact_listing_job(response["body"], row)
        checked.append(dict(row, **verdict))
        if pause:
            time.sleep(pause)
    return {"discoveredNewIndia": len(new), "alreadyPublished": sum(
        x["alreadyPublished"] for s in scans for x in s["jobs"]),
        "verifiedNew": [x for x in checked if x["state"] == "live"],
        "unconfirmedNew": [x for x in checked if x["state"] != "live"],
        "uncheckedNew": max(0, len(new)-len(checked))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pages", type=int, default=2)
    parser.add_argument("--companies", nargs="+", choices=list(DEFAULTS),
                        default=["EY", "Deloitte South Asia", "HCLTech"])
    parser.add_argument("--verify-new", type=int, default=3)
    parser.add_argument("--pause", type=float, default=0.5)
    parser.add_argument("--output", default="discovery-v3-full-list-report.json")
    parser.add_argument("--published", default="data/jobs.json")
    args = parser.parse_args()
    if args.max_pages < 1 or args.verify_new < 0 or args.pause < 0:
        parser.error("Expected max-pages >=1, verify-new >=0 and pause >=0")
    published = json.loads((ROOT / args.published).read_text())
    if not isinstance(published, list):
        raise SystemExit("Published jobs data must be an array")
    fetcher = AllowedHostFetcher()
    scans = [scan_employer(name, fetcher, args.max_pages, args.pause)
             for name in args.companies]
    outcomes = process(scans, published, fetcher, args.verify_new, args.pause)
    report = {"mode":"shadow_only","checkedAt":datetime.now(timezone.utc).isoformat(),
        "scans": scans,"summary": outcomes,
        "warning":"Incomplete sources never imply expiry. No production mutations or Telegram calls."}
    output = Path(args.output)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"companies":[{"company":s["employer"],"complete":s["complete"],
              "found":len(s["jobs"]),"reported":s["totalReported"],
              "problems":s["problems"]} for s in scans],
              "newIndia":outcomes["discoveredNewIndia"],
              "verifiedNew":len(outcomes["verifiedNew"])}, indent=2))


if __name__ == "__main__":
    main()
