"""V3 read-only publication gate from independent dated official-source scans.

No job changes, expiry updates, or production publishing are performed here.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

REQUIRED_EVIDENCE = {"canonical-match", "title-match", "apply-control"}
IST = ZoneInfo("Asia/Kolkata")


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Missing evidence timestamp")
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.utcoffset() is None:
        raise ValueError("Naive evidence time is not accepted")
    return t.astimezone(timezone.utc)


def inspect_history(reports, now=None):
    now = now or datetime.now(timezone.utc)
    chronological = sorted(reports, key=lambda r: timestamp(r["checkedAt"]))
    output = {"mode": "shadow_gate", "evaluatedAt": now.isoformat(),
              "runs": len(chronological), "employers": {},
              "publicationCandidates": [], "expiryDecisions": [],
              "safeToEnableAutomaticPublishing": False}

    companies = sorted({scan["employer"] for r in chronological
                        for scan in r.get("scans", [])})
    if any(r.get("mode") != "shadow_only" for r in chronological):
        raise ValueError("Cannot analyze production-mutating reports")

    for company in companies:
        runs = [dict(s, reportTime=r["checkedAt"]) for r in chronological
                for s in r.get("scans", []) if s.get("employer") == company]
        recent = runs[-3:]
        failures = []
        if len(recent) != 3:
            failures.append("Need three independent completed daily snapshots")
        if len(recent) == 3:
            scopes = {s.get("filter") for s in recent}
            days = {timestamp(s["reportTime"]).astimezone(IST).date() for s in recent}
            if len(scopes) != 1 or None in scopes:
                failures.append("Scope/filter changed between snapshots")
            if len(days) != 3:
                failures.append("Snapshots must originate from three different IST days")
            intervals = [(timestamp(b["reportTime"]) - timestamp(a["reportTime"])).total_seconds()
                         for a,b in zip(recent,recent[1:])]
            if any(value < 18 * 3600 or value > 36 * 3600 for value in intervals):
                failures.append("Snapshots must be approximately a day apart")
            if now - timestamp(recent[-1]["reportTime"]) > timedelta(hours=30):
                failures.append("Most recent official-source scan is stale")
            if any(not s.get("complete") or s.get("status") != "ok" for s in recent):
                failures.append("At least one source listing scan was partial or blocked")
            if any(s.get("pagesRead", 0) < 1 or
                   s.get("totalReported") != len(s.get("ids", [])) or
                   len(s.get("ids", [])) != len(set(s.get("ids", [])))
                   for s in recent):
                failures.append("Full listing counts or unique IDs not consistent")
            totals = [len(s.get("ids", [])) for s in recent]
            if totals and min(totals) * 2 < max(totals):
                failures.append("Large listing-count drop requires investigation")

        state = "eligible_for_further_checks" if not failures else "blocked"
        output["employers"][company] = {
            "status": state, "reasons": failures,
            "completeSnapshots": sum(bool(s.get("complete")) for s in recent),
            "latestCount": len(recent[-1].get("ids", [])) if recent else 0,
        }

        # Two consecutive complete-list absences ONLY create an independent
        # closure-review exception. Never auto-unpublish from listing diffs.
        if not failures and len(recent) == 3:
            older, before, latest = [set(s["ids"]) for s in recent]
            for missing in sorted((older - before) - latest):
                output["expiryDecisions"].append({
                    "employer": company, "id": missing, "action": "verify_closure",
                    "reason": "Absent in two successive complete daily crawls",
                })

    latest = chronological[-1] if chronological else {}
    scans = {s["employer"]: s for s in latest.get("scans", [])}
    for candidate in latest.get("summary", {}).get("verifiedNew", []):
        company = candidate.get("company")
        scan = scans.get(company)
        evidence = set(candidate.get("evidence", []))
        url = candidate.get("jobUrl", "")
        if not scan or candidate.get("alreadyPublished") or candidate.get("country") != "IN":
            continue
        if candidate.get("state") != "live" or not REQUIRED_EVIDENCE.issubset(evidence):
            continue
        # Incomplete scopes can yield leads; source feeds must pass the complete
        # scan gate before unattended publishing, even with verified exact pages.
        if output["employers"].get(company, {}).get("status") != "eligible_for_further_checks":
            continue
        if not url.startswith("https://"):
            continue
        output["publicationCandidates"].append({
            "company": company, "title": candidate.get("title"),
            "url": url, "evidence": sorted(evidence),
            "action": "prepare_source_grounded_draft_then_reverify",
        })

    # Other release gates (complete drafts, independent current-source verify,
    # retries, website and Telegram delivery) are not implemented by the
    # discovery scanner and must pass before a production scheduler can start.
    output["safeToEnableAutomaticPublishing"] = False
    output["remainingGates"] = [
        "Three complete daily scans from the exact same official scope",
        "Source-grounded publishing content for each vacancy",
        "Immediate independent exact-job verification before publishing",
        "Idempotent GitHub deployment and Telegram delivery integration test",
        "Manual review of unconfirmed or contradictory closure evidence",
    ]
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports", nargs="+", required=True)
    parser.add_argument("--output", default="discovery-v3-quality-gate.json")
    args = parser.parse_args()
    reports = [json.loads(Path(x).read_text()) for x in args.reports]
    result = inspect_history(reports)
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"runs": result["runs"],
                      "employers": result["employers"],
                      "candidates": len(result["publicationCandidates"]),
                      "expiryReviewOnly": len(result["expiryDecisions"]),
                      "autoPublishingEnabled": result["safeToEnableAutomaticPublishing"]},
                     indent=2))


if __name__ == "__main__":
    main()
