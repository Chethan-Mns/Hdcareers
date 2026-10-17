"""Read-only ten-job source checker benchmark against owner-confirmed ground truth."""
from __future__ import annotations
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_job_availability import check

FIXTURE = ROOT / "tests" / "fixtures" / "owner_manual_verification_20261013.json"
JOBS = ROOT / "data" / "jobs.json"
REPORT = ROOT / "owner-10-job-shadow-report.json"


def assess(owner, state, reason):
    if state not in ("active", "expired"):
        return "inconclusive"
    if state == "active" and "manual confirmation overrides" in str(reason):
        return "dependent_on_prior_manual_proof"
    return "match" if (owner == "live") == (state == "active") else "disagreement"


def run():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    jobs = {int(job["id"]): job for job in json.loads(JOBS.read_text(encoding="utf-8"))}
    rows = []
    for item in fixture["cases"]:
        job = jobs[int(item["id"])]
        if job["company"] != item["company"]:
            raise ValueError("Identity mismatch for owner fixture " + str(item["id"]))
        probe = check(job)
        verdict = assess(item["userVerdict"], probe["state"], probe.get("reason", ""))
        row = {
            "id": item["id"],
            "company": job["company"],
            "role": job["role"],
            "officialUrl": job["apply"],
            "ownerVerified": item["userVerdict"],
            "databaseStatusBeforeProbe": job["status"],
            "automatedState": probe["state"],
            "automatedReason": probe["reason"],
            "assessment": verdict,
            "checkedAt": probe["checkedAt"],
        }
        rows.append(row)
        print(f'{row["id"]} {row["company"]}: owner={row["ownerVerified"]}, automatic={row["automatedState"]}, assessment={verdict}', flush=True)
    totals = Counter(x["assessment"] for x in rows)
    result = {
        "mode": "shadow_only",
        "testedAt": datetime.now(timezone.utc).isoformat(),
        "ownerVerifiedOn": fixture["verifiedOn"],
        "summary": {"count": len(rows), **dict(totals)},
        "productionWrites": False,
        "telegramMessagesSent": 0,
        "results": rows,
    }
    REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2), flush=True)


if __name__ == "__main__":
    run()
