#!/usr/bin/env python3
"""Fingerprint the ATS/backend behind official job URLs.

Shadow diagnostic only. It never changes job state and never publishes.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from job_verifier_v2 import resolve, safe_url, UA

ROOT = Path(__file__).resolve().parents[1]

SIGNATURES = (
    ("workday", re.compile(r"myworkdayjobs\.com|/wday/cxs/|workday", re.I)),
    ("oracle_hcm", re.compile(r"oraclecloud\.com|/hcmRestApi/|CandidateExperience", re.I)),
    ("successfactors", re.compile(r"successfactors\.(?:com|eu)|/career\?|/sfcareer/|careerSiteBuilder|jobReqId", re.I)),
    ("greenhouse", re.compile(r"greenhouse\.io|boards-api\.greenhouse", re.I)),
    ("lever", re.compile(r"lever\.co|api\.lever\.co", re.I)),
    ("ashby", re.compile(r"ashbyhq\.com|api\.ashbyhq\.com", re.I)),
    ("smartrecruiters", re.compile(r"smartrecruiters\.com|api\.smartrecruiters", re.I)),
    ("phenom", re.compile(r"phenompeople\.com|phenom\.com|phncdn\.com", re.I)),
    ("icims", re.compile(r"icims\.com|icims\.net", re.I)),
    ("taleo", re.compile(r"taleo\.net|tbe\.taleo", re.I)),
)

JOB_API = re.compile(
    r"job|jobs|requisition|requisitions|posting|postings|position|positions|career|apply|candidate|vacanc",
    re.I,
)

REQ_PATTERNS = (
    re.compile(r"(?:job|jobs|jobdetail|position|requisition|req)[/_=-]([A-Za-z]*[-_]?[0-9][A-Za-z0-9_-]{2,})", re.I),
    re.compile(r"/([A-Z]{1,6}-?\d{4,})/?(?:[?#]|$)", re.I),
    re.compile(r"/(\d{5,})/?(?:[-/?#]|$)"),
)


def host(url):
    return (urlsplit(url).hostname or "").lower()


def direct_provider(url):
    ref = resolve(url)
    return ref.provider if ref else None


def signature(text):
    for name, rx in SIGNATURES:
        if rx.search(text):
            return name
    return None


def infer_req(job, url):
    vals = []
    for key in ("verificationTerms",):
        v = job.get(key)
        if isinstance(v, list):
            vals.extend(str(x) for x in v)
    vals.extend([str(job.get("sourceName") or ""), str(job.get("role") or ""), url])
    joined = " ".join(vals)
    for rx in REQ_PATTERNS:
        m = rx.search(joined)
        if m:
            return m.group(1)
    return None


def fingerprint(job, page, timeout_ms):
    url = str(job.get("apply") or "").strip()
    result = {
        "id": job.get("id"),
        "company": job.get("company"),
        "role": job.get("role"),
        "url": url,
        "source_host": host(url),
        "requisition_hint": infer_req(job, url),
        "direct_provider": direct_provider(url),
        "detected_provider": None,
        "confidence": "none",
        "signals": [],
        "job_api_requests": [],
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    if not url:
        result["error"] = "missing_url"
        return result
    try:
        safe_url(url)
    except Exception as exc:
        result["error"] = f"unsafe_url:{type(exc).__name__}"
        return result

    seen = set()
    responses = []

    def on_response(resp):
        u = resp.url
        if u in seen:
            return
        seen.add(u)
        sig = signature(u)
        if sig or JOB_API.search(urlsplit(u).path + "?" + (urlsplit(u).query or "")):
            responses.append({"url": u, "host": host(u), "status": resp.status, "signature": sig})

    page.on("response", on_response)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(1800)
        final_url = page.url
        title = page.title()
        html = page.content()
        scripts = page.locator("script[src]").evaluate_all("(els) => els.map(e => e.src)")
        body_text = page.locator("body").inner_text(timeout=4000)
        result["final_url"] = final_url
        result["title"] = title[:300]
        combined = " ".join([url, final_url, html[:500000], " ".join(scripts)])
        direct = result["direct_provider"]
        sigs = Counter()
        if direct:
            sigs[direct] += 10
            result["signals"].append(f"direct_url:{direct}")
        for item in responses:
            if item["signature"]:
                sigs[item["signature"]] += 4
                result["signals"].append(f"network:{item['signature']}:{item['host']}")
        for name, rx in SIGNATURES:
            if rx.search(combined):
                sigs[name] += 1
                result["signals"].append(f"page_asset:{name}")
        if sigs:
            provider, score = sigs.most_common(1)[0]
            result["detected_provider"] = provider
            result["confidence"] = "high" if score >= 4 else "medium"
        else:
            result["detected_provider"] = "custom_or_unknown"
            result["confidence"] = "low"
        result["job_api_requests"] = responses[:25]
        result["closure_text_seen"] = bool(re.search(
            r"no longer (?:available|posted|accepting applications)|position has been filled|job has been filled|applications? (?:are |is )?closed",
            body_text, re.I))
    except Exception as exc:
        result["error"] = type(exc).__name__
        result["job_api_requests"] = responses[:25]
        sigs = Counter(x["signature"] for x in responses if x["signature"])
        if sigs:
            result["detected_provider"] = sigs.most_common(1)[0][0]
            result["confidence"] = "high"
    finally:
        page.remove_listener("response", on_response)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", default=str(ROOT / "data" / "jobs.json"))
    ap.add_argument("--output", default=str(ROOT / "shadow-portal-fingerprints.json"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--timeout-ms", type=int, default=18000)
    args = ap.parse_args()

    jobs = json.loads(Path(args.jobs).read_text())
    if args.limit:
        jobs = jobs[:args.limit]

    from playwright.sync_api import sync_playwright
    rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=UA)
        page = context.new_page()
        for job in jobs:
            row = fingerprint(job, page, args.timeout_ms)
            rows.append(row)
            print(f"{row.get('company')} / {row.get('role')}: {row.get('detected_provider')} ({row.get('confidence')})")
        browser.close()

    counts = Counter(x.get("detected_provider") or "undetected" for x in rows)
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "jobs_scanned": len(rows),
        "provider_counts": dict(counts.most_common()),
        "rows": rows,
    }
    Path(args.output).write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"jobs_scanned": len(rows), "provider_counts": dict(counts.most_common())}, indent=2))


if __name__ == "__main__":
    main()
