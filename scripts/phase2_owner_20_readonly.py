"""Phase 2 owner-truth benchmark: no data writes or publication side effects.

Owner outcomes were verified on 2026-10-14; live web results are from
the time this workflow runs, and may legitimately differ after reopening.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_job_availability import check

FIXTURE = ROOT / "tests/fixtures/owner_phase2_manual_20_20261014.json"
JOBS = ROOT / "data/jobs.json"


def historic_assessment(recorded, truth):
    if recorded == "review":
        return "inconclusive_resolved_by_owner"
    if (recorded == "active") == (truth == "live"):
        return "correct"
    return "false_active" if recorded == "active" else "false_expired"


def current_db_assessment(status, truth):
    if (status == "active") == (truth == "live"):
        return "agrees_with_owner"
    return "incorrect_active" if status == "active" else "incorrect_expired"


def independent_probe(case, job):
    target = copy.deepcopy(job)
    for key in ("manualLiveVerifiedAt", "manualLiveVerifiedUrl",
                "browserVerifiedAt", "manualClosedVerifiedAt",
                "manualClosedVerifiedUrl"):
        target.pop(key, None)
    try:
        result = check(target)
        return {
            "state": result.get("state", "review"),
            "reason": result.get("reason", ""),
            "checkedAt": result.get("checkedAt"),
        }
    except Exception as exc:
        return {"state": "review", "reason": "Probe failed: " + type(exc).__name__,
                "checkedAt": datetime.now(timezone.utc).isoformat()}


def build_report(jobs, fixture, workers=6):
    by_id = {int(j["id"]): j for j in jobs}
    rows = []
    for sample in fixture["samples"]:
        job = by_id.get(sample["id"])
        if job is None:
            raise ValueError("Owner-verified job not in production: " + str(sample["id"]))
        if job.get("apply") != sample["url"]:
            raise ValueError("Exact employer URL changed for job " + str(sample["id"]))
        if job.get("company") != sample["company"]:
            raise ValueError("Employer mismatch for job " + str(sample["id"]))
        if sample["recordedChecker"] not in ("active", "expired", "review"):
            raise ValueError("Invalid historical checker state")
        if sample["userVerdict"] not in ("live", "expired"):
            raise ValueError("Invalid owner verdict")
        rows.append({
            "id": sample["id"], "company": sample["company"], "role": sample["role"],
            "officialUrl": sample["url"], "ownerVerifiedOn": fixture["verifiedOn"],
            "ownerVerdict": sample["userVerdict"],
            "historicalChecker": sample["recordedChecker"],
            "historicalAssessment": historic_assessment(sample["recordedChecker"], sample["userVerdict"]),
            "currentDatabase": job.get("status"),
            "currentDatabaseAssessment": current_db_assessment(job.get("status"), sample["userVerdict"]),
            "independentState": "not_checked", "independentReason": "",
        })
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(independent_probe, row, by_id[row["id"]]): row for row in rows}
        for future in as_completed(futures):
            row = futures[future]
            result = future.result()
            row["independentState"] = result["state"]
            row["independentReason"] = result["reason"]
            row["independentCheckedAt"] = result["checkedAt"]
            if result["state"] == "review":
                row["independentAssessment"] = "inconclusive"
            elif (result["state"] == "active") == (row["ownerVerdict"] == "live"):
                row["independentAssessment"] = "matches_prior_owner_observation"
            else:
                row["independentAssessment"] = "contradicts_prior_owner_observation_recheck_time_sensitive"
    rows.sort(key=lambda row: fixture["samples"].index(next(s for s in fixture["samples"] if s["id"] == row["id"])))
    return {
        "mode": "read_only_independent_shadow",
        "testedAt": datetime.now(timezone.utc).isoformat(),
        "ownerVerifiedOn": fixture["verifiedOn"],
        "productionWrites": False,
        "telegramMessagesSent": 0,
        "productionDeployments": 0,
        "summary": {
            "sample": len(rows),
            "historical": dict(Counter(x["historicalAssessment"] for x in rows)),
            "currentDatabase": dict(Counter(x["currentDatabaseAssessment"] for x in rows)),
            "independent": dict(Counter(x["independentAssessment"] for x in rows)),
            "independentDefinitive": sum(x["independentState"] != "review" for x in rows),
            "independentInconclusive": sum(x["independentState"] == "review" for x in rows),
        },
        "items": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="phase2-owner-20-shadow-results.json")
    parser.add_argument("--workers", type=int, choices=range(1, 9), default=6)
    args = parser.parse_args()
    jobs = json.loads(JOBS.read_text(encoding="utf-8"))
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    report = build_report(jobs, fixture, workers=args.workers)
    Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2, ensure_ascii=False), flush=True)
    for row in report["items"]:
        print(f'{row["id"]}: {row["company"]} owner={row["ownerVerdict"]}; saved={row["currentDatabase"]}; independent={row["independentState"]}: {row["independentReason"]}', flush=True)
    # This is a characterization run. The summary must not disguise unsafe
    # production states by reporting an entirely green "deployment ready" verdict.
    has_mismatch = report["summary"]["currentDatabase"].get("incorrect_expired", 0) > 0 or report["summary"]["currentDatabase"].get("incorrect_active", 0) > 0
    if has_mismatch:
        print("RELEASE BLOCKED: owner-truth database discrepancies remain; NO production changes made", flush=True)


if __name__ == "__main__":
    main()
