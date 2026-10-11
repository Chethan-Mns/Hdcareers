#!/usr/bin/env python3
"""Validate the ChatGPT 9 AM shortlist before it reaches HD Careers Admin.

No publishing, no job discovery, no generation, and no Telegram calls.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

DEFAULT = Path(__file__).resolve().parents[1] / "data" / "daily-review-batch.json"
ALLOWED_STATES = {"waiting", "reviewing", "submitted", "published"}
REVIEW_STATES = {"unreviewed", "live", "expired", "unsure"}
CAT_STATES = {"it", "nonit", "internship", "apprenticeship", "campus", "remote", "walkin", "experienced", "govt"}


def normalize(url: str) -> str:
    parsed = urlsplit(str(url or "").strip())
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Official job URL must use HTTPS")
    return parsed.hostname.lower() + parsed.path.rstrip("/").lower() + "?" + parsed.query


def check(payload: dict) -> dict:
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
    ids, urls, company_req = set(), set(), set()
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
        if row.get("reviewedStatus", "unreviewed") not in REVIEW_STATES:
            raise ValueError(f"Invalid review decision: {uid}")
        if not str(row.get("verificationReason") or "").strip():
            raise ValueError(f"Candidate {uid} needs a concrete verification reason")
        full = all(str(job.get(k) or "").strip() for k in ("company", "role", "loc", "elig", "desc", "apply"))
        full = full and isinstance(job.get("resp"), list) and bool(job["resp"])
        if full:
            ready += 1
    if state in ("submitted", "published"):
        if len(priority) != 10 or any(j.get("reviewedStatus") != "live" for j in priority):
            raise ValueError("Submitted batch requires 10 manually reviewed LIVE priority jobs")
        if any(not all(str(j["job"].get(k) or "").strip() for k in ("loc", "elig", "desc", "apply"))
               or not j["job"].get("resp") for j in priority):
            raise ValueError("Submitted batch cannot include incomplete jobs")
    return {"state": state, "priority": len(priority), "backup": len(backup),
            "complete": ready, "unreviewed": sum(x.get("reviewedStatus", "unreviewed") == "unreviewed" for x in priority + backup)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default=str(DEFAULT))
    args = parser.parse_args()
    try:
        result = check(json.loads(Path(args.path).read_text(encoding="utf-8")))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.exit(status=1, message=f"Invalid daily review shortlist: {error}\n")
    print(json.dumps({"ok": True, **result}))


if __name__ == "__main__":
    main()
