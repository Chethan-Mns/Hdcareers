#!/usr/bin/env python3
"""Create an existing-publisher event from a human-approved partial daily batch.

Only the named, LIVE, fully documented jobs are eligible. This script does not
publish anything; scripts/admin_publish.py independently rechecks official URLs.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DAILY = ROOT / "data" / "daily-review-batch.json"
PUBLISHED = ROOT / "data" / "jobs.json"
REQUIRED = [
    "page", "domain", "company", "salary", "logo", "role", "roleTag",
    "loc", "locationFilter", "batch", "elig", "cat", "expType",
    "expYears", "date", "desc", "resp", "apply", "status",
    "verifiedDate", "sourceName", "skills", "who", "workMode",
]


def load(path: Path, expected: type):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, expected):
        raise ValueError(f"{path.name} must contain {expected.__name__}")
    return data


def prepare(request_path: Path, output_path: Path) -> dict:
    request = load(request_path, dict)
    batch = load(DAILY, dict)
    published = load(PUBLISHED, list)
    batch_id = str(request.get("batchId") or "").strip()
    chosen = request.get("candidateIds")
    if batch_id != "2026-10-11-0900-ist" or batch.get("batchId") != batch_id:
        raise ValueError("Authorized 11 October batch does not match the saved Admin review batch")
    if request.get("approvedBy") != "HD Careers Owner":
        raise ValueError("Owner publication approval is missing")
    if request.get("requestId") != "approved-nine-20261011":
        raise ValueError("Unexpected publication request ID")
    if not isinstance(chosen, list) or len(chosen) != 9:
        raise ValueError("Owner authorized exactly nine jobs")
    if len(set(chosen)) != 9 or any(not isinstance(x, str) or not x.strip() for x in chosen):
        raise ValueError("Selected candidate IDs must be nine distinct nonblank strings")
    if "unisys-REQ568332" in chosen:
        raise ValueError("Unisys is excluded: its exact requisition description remains unconfirmed")
    source = {str(x.get("id")): x for x in batch.get("priority", [])}
    if len(source) != len(batch.get("priority", [])):
        raise ValueError("Duplicate candidate IDs found in Admin priority list")
    urls = {str(x.get("apply") or "").strip().rstrip("/").lower() for x in published}
    pairs = {(str(x.get("company") or "").strip().casefold(),
              str(x.get("role") or "").strip().casefold()) for x in published}
    company_names = set()
    picked = []
    for cid in chosen:
        item = source.get(cid)
        if not item or item.get("reviewedStatus") != "live" or not item.get("reviewedAt"):
            raise ValueError(f"Job {cid} has not been explicitly marked LIVE in priority review")
        job = item.get("job")
        if not isinstance(job, dict) or job.get("status") != "active":
            raise ValueError(f"Job {cid} is not an active, reviewed publishing record")
        missing = [key for key in REQUIRED if key not in job]
        if missing:
            raise ValueError(f"Job {cid} has missing publication fields: {', '.join(missing)}")
        if not all(str(job.get(key) or "").strip() for key in ("company", "role", "loc", "elig", "desc", "apply", "who", "sourceName")):
            raise ValueError(f"Job {cid} has empty publication data")
        if not isinstance(job.get("resp"), list) or not job["resp"]:
            raise ValueError(f"Job {cid} is missing verified job responsibilities")
        apply = str(job["apply"]).strip()
        parsed = urlsplit(apply)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError(f"Job {cid} is missing a direct HTTPS career URL")
        company = str(job["company"]).strip().casefold()
        if company in company_names:
            raise ValueError(f"More than one job selected from {job['company']}")
        company_names.add(company)
        if apply.rstrip("/").lower() in urls or (company, str(job["role"]).strip().casefold()) in pairs:
            raise ValueError(f"Job {cid} already appears in production and will not be republished")
        # This attaches the exact official URL to the earlier recorded HUMAN
        # decision, without changing the timestamp or inventing any new review.
        approved = dict(job)
        if approved.get("manualLiveVerifiedAt") != item.get("reviewedAt"):
            raise ValueError(f"Human verification timestamp mismatch: {cid}")
        if approved.get("apply") != item.get("apply"):
            raise ValueError(f"Official URL changed after human review: {cid}")
        approved["manualLiveVerifiedUrl"] = apply
        picked.append(approved)
    event = {"event_type": "admin_publish_jobs", "client_payload": {"jobs": picked}}
    output_path.write_text(json.dumps(event, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"batchId": batch_id, "jobCount": len(picked),
            "companies": [j["company"] for j in picked], "excluded": ["Unisys"]}


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: prepare_review_publication.py <request.json> <event-output.json>")
    try:
        print(json.dumps(prepare(Path(sys.argv[1]), Path(sys.argv[2]))))
    except (ValueError, OSError, KeyError) as e:
        raise SystemExit("Publishing safely blocked: " + str(e))


if __name__ == "__main__":
    main()
