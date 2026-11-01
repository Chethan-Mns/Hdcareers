#!/usr/bin/env python3
"""Read-only official ATS discovery pilot inspired by FreeHire's MIT-licensed adapter design.

Source boards are learned from existing HD Careers official Apply URLs, NOT from
FreeHire's hosted job catalogue. Nothing here publishes, marks jobs expired, or
modifies the admin review queue. All candidates are unreviewed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ATS_HOSTS = {
    "greenhouse": {"job-boards.greenhouse.io", "job-boards.eu.greenhouse.io", "boards.greenhouse.io"},
    "lever": {"jobs.lever.co", "jobs.eu.lever.co"},
    "ashby": {"jobs.ashbyhq.com"},
    "smartrecruiters": {"jobs.smartrecruiters.com"},
}
BOARD_RE = re.compile(r"^[A-Za-z0-9_-]{2,100}$")
WORKDAY_HOST_RE = re.compile(r"^(?P<tenant>[a-z0-9-]+)\.wd\d+\.myworkdayjobs\.com$")
INDIA_RE = re.compile(
    r"\b(india|bharat|bengaluru|bangalore|hyderabad|chennai|pune|mumbai|noida|"
    r"gurugram|gurgaon|delhi|kolkata|kochi|cochin|ahmedabad|jaipur|coimbatore|"
    r"thiruvananthapuram|trivandrum|visakhapatnam|vizag|bhubaneswar|lucknow|"
    r"nagpur|mysore|mysuru|navi mumbai)\b", re.I)
JUNIOR_RE = re.compile(
    r"\b(intern(?:ship)?|apprentice(?:ship)?|graduate|freshers?|trainee|"
    r"entry.level|early.career|junior|new associate|associate software engineer|"
    r"software engineer i|analyst i|campus)\b", re.I)
SENIOR_RE = re.compile(
    r"\b(senior|sr\.?|staff|principal|lead|manager|director|architect|head of|"
    r"vice president|vp|experienced hire)\b", re.I)
EXP_RE = re.compile(r"\b(\d{1,2})\s*(?:(?:to|-|–)\s*(\d{1,2})|\+)?\s*years?\s*(?:of )?(?:relevant |professional |work )?experience\b", re.I)
EXTERNAL_APPLY_HOSTS = set().union(*ATS_HOSTS.values())
API_ALLOWLIST = {
    "boards-api.greenhouse.io",
    "api.lever.co", "api.eu.lever.co", "api.ashbyhq.com",
    "api.smartrecruiters.com",
}
SOURCE_PROVIDER = {"greenhouse", "lever", "ashby", "smartrecruiters", "workday"}


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.skip += 1
        elif tag in {"p", "br", "li", "h1", "h2", "h3"}:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.skip:
            self.skip -= 1
        elif tag in {"p", "li"}:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def clean_html(value):
    parser = PlainText()
    parser.feed(unescape(str(value or "")))
    return " ".join("".join(parser.parts).split())[:10000]


def canonical(url):
    p = urlsplit(str(url or "").strip())
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        return ""
    return urlunsplit(("https", p.hostname.lower(), p.path.rstrip("/"), "", ""))


def parse_board(company, apply_url):
    p = urlsplit(str(apply_url or ""))
    if p.scheme != "https" or p.username or p.password:
        return None
    host = (p.hostname or "").lower()
    parts = [part for part in p.path.split("/") if part]
    provider = next((name for name, hosts in ATS_HOSTS.items() if host in hosts), "")
    if provider:
        if len(parts) < 2 or not BOARD_RE.fullmatch(parts[0]):
            return None
        board = parts[0]
        if provider == "greenhouse" and (len(parts) < 3 or parts[1] != "jobs"):
            return None
        if provider == "smartrecruiters" and len(parts) < 2:
            return None
        if provider == "lever" and len(parts) < 2:
            return None
        if provider == "ashby" and len(parts) < 2:
            return None
        return {"company": company, "provider": provider, "board": board,
                "region": "eu" if host == "jobs.eu.lever.co" else ""}
    match = WORKDAY_HOST_RE.fullmatch(host)
    if match:
        if len(parts) > 2 and re.fullmatch(r"[a-z]{2}-[A-Z]{2}", parts[0]):
            parts = parts[1:]
        if len(parts) >= 3 and parts[1] == "job" and BOARD_RE.fullmatch(parts[0]):
            return {"company": company, "provider": "workday", "board": parts[0],
                    "tenant": match.group("tenant"), "host": host}
    return None


def boards_from_jobs(jobs, providers=SOURCE_PROVIDER):
    boards = {}
    for row in jobs:
        if not isinstance(row, dict):
            continue
        company = str(row.get("company") or "").strip()
        if not company:
            continue
        board = parse_board(company, row.get("apply"))
        if not board or board["provider"] not in providers:
            continue
        key = (board["provider"], board.get("host", ""), board["board"].lower())
        # Multiple legacy jobs can point to the same board. One board is one crawl.
        boards.setdefault(key, board)
    return sorted(boards.values(), key=lambda x: (
        x["company"].lower() != "deloitte", x["company"].lower(),
        x["provider"], x["board"].lower()))


def fetch_json(url, body=None, *, timeout=15):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.username or parsed.password:
        raise ValueError("Non-HTTPS or credentialed API URL")
    host = (parsed.hostname or "").lower()
    if host not in API_ALLOWLIST and not WORKDAY_HOST_RE.fullmatch(host):
        raise ValueError("API host is not allowlisted")
    headers = {"Accept": "application/json", "User-Agent": "HDCareersATSResearch/1.0"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method="POST" if data else "GET")
    # No HTTP redirects to arbitrary hosts or authentication bypasses.
    with urlopen(req, timeout=timeout) as response:
        if (urlsplit(response.url).hostname or "").lower() not in API_ALLOWLIST and not WORKDAY_HOST_RE.fullmatch((urlsplit(response.url).hostname or "").lower()):
            raise ValueError("API redirected outside approved hosts")
        return json.load(response)


def is_india(location, country=""):
    if str(country).strip().lower() in {"in", "ind", "india"}:
        return True
    if country and str(country).strip().lower() not in {"in", "ind", "india"}:
        return False
    return bool(INDIA_RE.search(str(location or "")))


def fresher_signal(title, description):
    """A heuristic to generate review candidates, not proof of eligibility."""
    if SENIOR_RE.search(title):
        return ""
    # An explicit 4+ year minimum is inconsistent with the HD fresher policy.
    years = [(int(m.group(1)), int(m.group(2) or m.group(1)))
             for m in EXP_RE.finditer(description[:5500])]
    if any(max(lo, hi) > 3 for lo, hi in years):
        return ""
    if JUNIOR_RE.search(title):
        return "title_match_requires_manual_eligibility_check"
    if years and min(lo for lo, _ in years) <= 2:
        return "description_years_requires_manual_eligibility_check"
    return ""


def category_hint(title):
    if re.search(r"\b(intern|internship|apprentice|apprenticeship)\b", title, re.I):
        return "internship"
    if re.search(r"\b(operations|finance|accounting|customer support|hr |human resources|sales|collections)\b", title, re.I):
        return "nonit"
    return "technical"


def normalize_posting(board, row):
    provider = board["provider"]
    url = canonical(row.get("url"))
    host = (urlsplit(url).hostname or "").lower() if url else ""
    if not url or (host not in EXTERNAL_APPLY_HOSTS and not WORKDAY_HOST_RE.fullmatch(host)):
        return None
    # Only accept apply URLs on the *same employer board*, never third-party redirects.
    parsed_board = parse_board(board["company"], url)
    if parsed_board is None or parsed_board["provider"] != provider or parsed_board["board"].lower() != board["board"].lower():
        return None
    if provider == "workday" and parsed_board.get("host") != board.get("host"):
        return None
    title = clean_html(row.get("title"))[:220]
    location = clean_html(row.get("location"))[:300]
    description = clean_html(row.get("description"))
    if not title or not is_india(location, row.get("country")):
        return None
    signal = fresher_signal(title, description)
    if not signal:
        return None
    external_id = str(row.get("id") or "").strip()
    if not external_id:
        return None
    fingerprint = hashlib.sha256((provider + "\n" + board["board"].lower() + "\n" + external_id).encode()).hexdigest()[:24]
    return {
        "id": "ats-" + fingerprint,
        "company": board["company"], "role": title, "loc": location,
        "apply": url, "externalId": external_id, "sourceProvider": provider,
        "sourceBoard": board["board"], "sourceName": board["company"] + " official ATS",
        "categoryHint": category_hint(title),
        "fresherSignal": signal, "eligibilityStatus": "needs_manual_verification",
        "reviewedStatus": "unreviewed", "sourceStatus": "listed_on_official_ATS",
        "descriptionExcerpt": description[:1200],
        "publishedAtSource": str(row.get("posted") or "")[:64],
    }


def source_posts(board, *, fetcher=fetch_json, max_pages=5, max_details=12):
    """Return (raw_postings, notes, complete). Incomplete scans must not imply expiry."""
    provider, slug = board["provider"], quote(board["board"], safe="")
    if provider == "greenhouse":
        data = fetcher(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
        if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
            raise ValueError("Greenhouse listing array absent")
        return ([{
            "id": str(j.get("id") or ""), "url": j.get("absolute_url"),
            "title": j.get("title"), "location": (j.get("location") or {}).get("name", ""),
            "description": j.get("content", ""), "posted": j.get("updated_at", ""),
        } for j in data["jobs"] if isinstance(j, dict)], [], True)
    if provider == "lever":
        host = "api.eu.lever.co" if board.get("region") == "eu" else "api.lever.co"
        data = fetcher(f"https://{host}/v0/postings/{slug}?mode=json")
        if not isinstance(data, list):
            raise ValueError("Lever listing array absent")
        return ([{
            "id": j.get("id"), "url": j.get("hostedUrl"), "title": j.get("text"),
            "location": (j.get("categories") or {}).get("location", ""),
            "country": j.get("country", ""),
            "description": " ".join([j.get("description") or "",
                " ".join((a.get("text") or "") + " " + (a.get("content") or "")
                         for a in (j.get("lists") or []) if isinstance(a, dict)),
                j.get("additional") or ""]),
            "posted": j.get("createdAt", ""),
        } for j in data if isinstance(j, dict)], [], True)
    if provider == "ashby":
        data = fetcher(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
        if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
            raise ValueError("Ashby listing array absent")
        return ([{
            "id": j.get("id"), "url": j.get("jobUrl"), "title": j.get("title"),
            "location": j.get("location", ""),
            "country": ((j.get("address") or {}).get("postalAddress") or {}).get("addressCountry", ""),
            "description": j.get("descriptionHtml") or j.get("descriptionPlain", ""),
            "posted": j.get("publishedAt", ""),
        } for j in data["jobs"] if isinstance(j, dict)], [], True)
    if provider == "smartrecruiters":
        all_posts, notes, complete = [], [], True
        for page in range(max_pages):
            offset = len(all_posts)
            data = fetcher(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100&offset={offset}")
            if not isinstance(data, dict) or not isinstance(data.get("content"), list) or not isinstance(data.get("totalFound"), int):
                raise ValueError("SmartRecruiters listing contract absent")
            all_posts.extend(j for j in data["content"] if isinstance(j, dict))
            if len(all_posts) >= data["totalFound"]:
                break
            if not data["content"]:
                complete = False
                notes.append("Listing ended before reported total; not an expiry signal")
                break
        else:
            complete = False
            notes.append("Listing page budget reached; scan is partial")
        selected = []
        for j in all_posts:
            l = j.get("location") or {}
            place = ", ".join(str(x) for x in (l.get("city"), l.get("region"), l.get("country")) if x)
            if is_india(place, l.get("country", "")) and fresher_signal(str(j.get("name") or ""), ""):
                selected.append((j, place))
        if len(selected) > max_details:
            complete = False
            notes.append("Per-board detail budget reached; remaining candidates not checked")
        out = []
        for j, place in selected[:max_details]:
            external_id = str(j.get("id") or "")
            if not external_id:
                continue
            try:
                detail = fetcher(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings/{quote(external_id, safe='')}")
                sec = ((detail.get("jobAd") or {}).get("sections") or {})
                desc = " ".join(str((sec.get(x) or {}).get("text") or "") for x in
                    ("jobDescription", "qualifications", "additionalInformation"))
                if not desc:
                    desc = str((sec.get("companyDescription") or {}).get("text") or "")
                if not detail.get("postingUrl"):
                    notes.append("Unverifiable detail held: " + external_id)
                    continue
                out.append({"id": external_id, "url": detail["postingUrl"],
                    "title": j.get("name"), "location": place, "country": (j.get("location") or {}).get("country", ""),
                    "description": desc, "posted": j.get("releasedDate", "")})
            except (ValueError, HTTPError, URLError, TimeoutError) as e:
                complete = False
                notes.append("Detail request failed; listing held: " + external_id + " (" + type(e).__name__ + ")")
        return out, notes, complete
    if provider == "workday":
        host, tenant, site = board["host"], board["tenant"], slug
        endpoint = f"https://{host}/wday/cxs/{quote(tenant, safe='')}/{site}/jobs"
        all_posts, notes, complete = [], [], True
        total = None
        for page in range(max_pages):
            data = fetcher(endpoint, {"appliedFacets": {}, "limit": 20, "offset": page * 20, "searchText": ""})
            if not isinstance(data, dict) or not isinstance(data.get("jobPostings"), list) or not isinstance(data.get("total"), int):
                raise ValueError("Workday listing contract absent")
            total = data["total"]
            all_posts.extend(x for x in data["jobPostings"] if isinstance(x, dict))
            if len(all_posts) >= total:
                break
            if not data["jobPostings"]:
                complete = False
                notes.append("Workday empty page before reported total; scan incomplete")
                break
        else:
            complete = False
            notes.append("Workday page budget reached; scan incomplete")
        if total is not None and total >= 2000:
            complete = False
            notes.append("Workday 2000-result cap may require facet subdivision")
        chosen = []
        for j in all_posts:
            loc = str(j.get("locationsText") or "")
            if is_india(loc) and fresher_signal(str(j.get("title") or ""), ""):
                chosen.append(j)
        if len(chosen) > max_details:
            complete = False
            notes.append("Workday detail budget reached")
        out = []
        for j in chosen[:max_details]:
            path = str(j.get("externalPath") or "")
            if not path.startswith("/job/"):
                notes.append("Workday invalid externalPath held")
                continue
            try:
                d = fetcher(f"https://{host}/wday/cxs/{quote(tenant, safe='')}/{site}{path}")
                info = d.get("jobPostingInfo") or {}
                if not info.get("title") or not info.get("jobDescription"):
                    notes.append("Workday detail missing title/description held")
                    continue
                out.append({"id": path, "url": f"https://{host}/{board['board']}{path}",
                    "title": info["title"], "location": j.get("locationsText", ""),
                    "description": info["jobDescription"], "posted": info.get("startDate", "")})
            except (ValueError, HTTPError, URLError, TimeoutError) as e:
                complete = False
                notes.append("Workday detail failed: " + type(e).__name__)
        return out, notes, complete
    raise ValueError("Unsupported ATS provider")


def discover(jobs, *, fetcher=fetch_json, providers=SOURCE_PROVIDER, max_boards=30,
             max_pages=5, max_details=12):
    if max_boards < 1 or max_pages < 1 or max_details < 1:
        raise ValueError("Crawl budgets must be positive")
    boards = boards_from_jobs(jobs, providers)
    site_urls = {canonical(x.get("apply")) for x in jobs if isinstance(x, dict)}
    # Existing site identity is also employer + role when a requisition ID is absent.
    site_pairs = {(str(x.get("company") or "").lower().strip(),
                   str(x.get("role") or "").lower().strip())
                  for x in jobs if isinstance(x, dict)}
    results, scans, seen, seen_roles = [], [], set(), set()
    for board in boards[:max_boards]:
        started = time.monotonic()
        scan = {"company": board["company"], "provider": board["provider"],
                "board": board["board"], "status": "ok", "complete": False,
                "listed": 0, "newReviewCandidates": 0, "duplicateOnSite": 0,
                "duplicateInDiscovery": 0,
                "notes": [], "elapsedSeconds": 0}
        try:
            posts, notes, complete = source_posts(board, fetcher=fetcher,
                max_pages=max_pages, max_details=max_details)
            scan["listed"] = len(posts)
            scan["notes"] = notes[:50]
            scan["complete"] = complete
            scan["status"] = "ok" if complete else "partial"
            for post in posts:
                candidate = normalize_posting(board, post)
                if not candidate:
                    continue
                key = canonical(candidate["apply"])
                pair = (candidate["company"].lower(), candidate["role"].lower())
                if key in site_urls or pair in site_pairs:
                    scan["duplicateOnSite"] += 1
                    continue
                if key in seen or pair in seen_roles:
                    scan["duplicateInDiscovery"] = scan.get("duplicateInDiscovery", 0) + 1
                    continue
                seen.add(key)
                seen_roles.add(pair)
                scan["newReviewCandidates"] += 1
                results.append(candidate)
        except (ValueError, HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            scan["status"] = "error"
            scan["complete"] = False
            scan["notes"].append(type(error).__name__ + ": " + str(error)[:250])
        scan["elapsedSeconds"] = round(time.monotonic() - started, 2)
        scans.append(scan)
    return {
        "mode": "shadow_only", "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "Official ATS APIs from existing HD Careers employer job links",
        "license": "Independent client; no FreeHire hosted job catalogue or API used",
        "totalSeedBoards": len(boards), "scannedBoards": len(scans),
        "unscannedBoards": max(0, len(boards) - len(scans)),
        "partialOrFailedBoards": sum(not s["complete"] for s in scans),
        "candidateCount": len(results), "scans": scans, "candidates": results,
        "publicationAllowed": False, "expiryDecisionsAllowed": False,
        "notes": [
            "Only heuristic discovery candidates. Freshers, India location, source URL and completeness require independent validation.",
            "A failed, capped, or partial crawl NEVER implies a previously published job is expired.",
            "No writes to jobs.json, review queue, Admin, Telegram or website.",
            "Employer ATS API use remains subject to each host's terms and rate limits.",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs", default=str(ROOT / "data/jobs.json"))
    parser.add_argument("--providers", default="greenhouse,lever,ashby,smartrecruiters,workday")
    parser.add_argument("--max-boards", type=int, default=30)
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--max-details", type=int, default=12)
    parser.add_argument("--output", default="ats-discovery-shadow.json")
    parser.add_argument("--catalog-only", action="store_true", help="No network; report supported ATS boards seeded by HD Careers")
    args = parser.parse_args()
    with open(args.jobs, encoding="utf-8") as f:
        jobs = json.load(f)
    if not isinstance(jobs, list):
        parser.error("--jobs must reference a JSON array")
    providers = {x.strip() for x in args.providers.split(",") if x.strip()}
    if not providers or not providers <= SOURCE_PROVIDER:
        parser.error("Invalid providers list")
    if args.catalog_only:
        catalog = boards_from_jobs(jobs, providers)
        result = {"mode": "catalog_only", "totalSeedBoards": len(catalog), "boards": catalog,
                  "publicationAllowed": False, "expiryDecisionsAllowed": False}
    else:
        result = discover(jobs, providers=providers, max_boards=args.max_boards,
            max_pages=args.max_pages, max_details=args.max_details)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: result.get(k) for k in
                      ("mode", "totalSeedBoards", "scannedBoards", "candidateCount", "partialOrFailedBoards")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
