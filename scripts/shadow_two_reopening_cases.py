"""Read-only exact source verification of owner-disputed closed jobs.

The owner's last Live observation is historical and NOT an assertion that the
job remains open indefinitely. Do not change production based on this report.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_job_availability import check

ROOT = Path(__file__).resolve().parents[1]
WANTED = {82: "NielsenIQ", 75: "Deloitte USI"}

def main():
    jobs = {int(j["id"]): j for j in json.loads((ROOT / "data/jobs.json").read_text())}
    records = []
    for ident, company in WANTED.items():
        job = jobs[ident]
        assert job["company"] == company
        assert job["status"] == "expired"
        assert job["apply"].startswith("https://")
        result = check(job)
        records.append({
            "id": ident, "company": company, "exactUrl": job["apply"],
            "ownerPreviouslyVerified": "Live, 14 Oct 2026",
            "storedDatabase": job["status"],
            "independentState": result["state"],
            "independentReason": result["reason"],
            "checkedAt": result["checkedAt"],
            "automaticReopeningApproved": (
                result["state"] == "active" and
                result["reason"].startswith("Reopening confirmed:") and
                not job.get("manualClosedVerifiedAt")
            ),
            "reviewRequired": result["state"] != "active",
        })
        print(ident, company, result["state"], result["reason"], flush=True)
    report = {
        "mode": "read_only_shadow", "source": "official exact employer URLs",
        "testedAt": datetime.now(timezone.utc).isoformat(),
        "productionWrites": False, "telegramMessagesSent": 0,
        "items": records,
    }
    Path("phase2-nielsen-deloitte-shadow.json").write_text(json.dumps(report, indent=2) + "\n")
    if any(r["independentState"] == "expired" for r in records):
        raise SystemExit("Potential historic false-expired verdict; require explicit new owner review, not automatic closure")

if __name__ == "__main__":
    main()
