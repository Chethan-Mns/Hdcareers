#!/usr/bin/env python3
"""Validate the ChatGPT 9 AM shortlist before it reaches HD Careers Admin.

No publishing, no job discovery, no generation, and no Telegram calls.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit
import re


DEFAULT = Path(__file__).resolve().parents[1] / "data" / "daily-review-batch.json"
ALLOWED_STATES = {"waiting", "reviewing", "submitted", "published"}
REVIEW_STATES = {"unreviewed", "live", "expired", "unsure"}
CAT_STATES = {"it", "nonit", "internship", "apprenticeship", "campus", "remote", "walkin", "experienced", "govt"}


def normalize(url: str) -> str:
    parsed = urlsplit(str(url or "").strip())
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Official job URL must use HTTPS")
    return parsed.hostname.lower() + parsed.path.rstrip("/").lower() + "?" + parsed.query


def employer_key(value):
    text = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower().replace("&", " and ")).strip()
    text = re.sub(r"\b(pvt|private|ltd|limited|inc|llp|corp|corporation)\b", " ", text)
    text = " ".join(text.split())
    return {
        "tcs": "tata consultancy services",
        "hcl": "hcltech", "hcl technologies": "hcltech",
        "ey": "ernst young", "ernst and young": "ernst young",
        "ibm": "international business machines",
        "pwc": "pricewaterhousecoopers",
        "ntt data": "nttdata", "deloitte usi": "deloitte",
        "google india": "google", "amazon india": "amazon",
        "cognizant technology solutions": "cognizant"
    }.get(text, text)


def fresher_it(row):
    job = row.get("job") or {}
    category = str(job.get("cat") or row.get("cat") or "it").lower()
    exp = str(job.get("expYears") or row.get("expYears") or "").strip().lower()
    return category in {"it", "campus", "remote"} and (
        job.get("expType") == "fresher" or exp in {"fresher", "0 years", "0 year", "early career"}
    )


def check(payload: dict, strict_discovery: bool = False) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Batch must be a JSON object")
    state = payload.get("status", "waiting")
    if state not in ALLOWED_STATES:
        raise ValueError("Unsupported review batch status")
    if not isinstance(payload.get("priority"), list) or not isinstance(payload.get("backup"), list):
        raise ValueError("Both priority and backup must be lists")
    priority, backup = payload["priority"], payload["backup"]
    if len(priority) > 10 or len(backup) > 10:
        raise ValueError("Maximum 10 priority and 10 backup candidates")
    if state == "waiting":
        if payload.get("batchId") or priority or backup:
            raise ValueError("Waiting batch must be empty")
        return {"state": state, "priority": 0, "backup": 0, "complete": 0}
    if not str(payload.get("batchId") or "").strip():
        raise ValueError("Non-empty batchId is required")
    if not payload.get("generatedAt"):
        raise ValueError("Every shortlist must have a generatedAt timestamp")
    if not priority:
        raise ValueError("At least one real priority candidate is required")
    ids, urls, company_req, employers = set(), set(), set(), {}
    ready = 0
    for index, row in enumerate(priority + backup, 1):
        if not isinstance(row, dict):
            raise ValueError(f"Candidate {index} must be an object")
        uid = str(row.get("id") or "").strip()
        if not uid or uid in ids:
            raise ValueError(f"Candidate {index} has a blank or duplicate ID")
        ids.add(uid)
        job = row.get("job")
        if not isinstance(job, dict):
            raise ValueError(f"Candidate {uid} must contain a job object, even if details are incomplete")
        for field in ("company", "role", "apply"):
            if not str(job.get(field) or row.get(field) or "").strip():
                raise ValueError(f"Candidate {uid} is missing {field}")
        url = normalize(job.get("apply") or row.get("apply"))
        if url in urls:
            raise ValueError(f"Duplicate official apply URL in shortlist: {uid}")
        urls.add(url)
        pair = (str(job.get("company") or row.get("company")).lower().strip(),
                str(job.get("jobId") or row.get("jobId") or job.get("role") or row.get("role")).lower().strip())
        if pair in company_req:
            raise ValueError(f"Duplicate employer + requisition / role: {uid}")
        company_req.add(pair)
        employer = employer_key(job.get("company") or row.get("company"))
        if not employer:
            raise ValueError(f"Candidate {uid} has no identifiable employer")
        if strict_discovery and employer in employers:
            raise ValueError(f"Repeated employer across Priority and Backup: {uid} duplicates {employers[employer]}")
        employers.setdefault(employer, uid)
        if row.get("reviewedStatus", "unreviewed") not in REVIEW_STATES:
            raise ValueError(f"Invalid review decision: {uid}")
        if not str(row.get("verificationReason") or "").strip():
            raise ValueError(f"Candidate {uid} needs a concrete verification reason")
        full = all(str(job.get(k) or "").strip() for k in ("company", "role", "loc", "elig", "desc", "apply"))
        full = full and isinstance(job.get("resp"), list) and bool(job["resp"])
        if full:
            ready += 1
    if strict_discovery:
        if len(priority) != 10 or len(backup) != 10 or len(employers) != 20:
            raise ValueError("Discovery requires 10 priority + 10 backup jobs from 20 different employers")
        available = sum(fresher_it(j) for j in priority + backup)
        selected_freshers = sum(fresher_it(j) for j in priority)
        if selected_freshers < min(8, available):
            raise ValueError(f"Fresher IT preference not met: {selected_freshers}/10 priority, {available} verified candidates available")
    if state in ("submitted", "published"):
        publication = payload.get("publication") or {}
        chosen = publication.get("candidateIds")
        if not isinstance(chosen, list) or not 1 <= len(chosen) <= 10 or len(set(chosen)) != len(chosen):
            raise ValueError("Submitted batch requires an explicit 1-10 job selection")
        candidates = {str(j.get("id")): j for j in priority + backup}
        picked = [candidates.get(cid) for cid in chosen]
        if any(j is None or j.get("reviewedStatus") != "live" or not j.get("reviewedAt") for j in picked):
            raise ValueError("Submitted jobs must be explicitly reviewed LIVE")
        if len({employer_key(j["job"].get("company")) for j in picked}) != len(picked):
            raise ValueError("Only one approved job per employer is allowed")
        if any(not all(str(j["job"].get(k) or "").strip() for k in ("company", "role", "loc", "elig", "desc", "apply", "sourceName"))
               or not j["job"].get("resp") or j["job"].get("status") != "active" for j in picked):
            raise ValueError("Submitted batch cannot include incomplete or inactive jobs")
    return {"state": state, "priority": len(priority), "backup": len(backup),
            "uniqueEmployers": len(employers), "fresherITPriority": sum(fresher_it(j) for j in priority),
            "complete": ready, "unreviewed": sum(x.get("reviewedStatus", "unreviewed") == "unreviewed" for x in priority + backup)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default=str(DEFAULT))
    parser.add_argument("--strict-discovery", action="store_true", help="Validate 20 unique employers and Fresher IT preference")
    args = parser.parse_args()
    try:
        result = check(json.loads(Path(args.path).read_text(encoding="utf-8")), strict_discovery=args.strict_discovery)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.exit(status=1, message=f"Invalid daily review shortlist: {error}\n")
    print(json.dumps({"ok": True, **result}))


if __name__ == "__main__":
    main()
