#!/usr/bin/env python3
"""Durable, read-only ATS discovery history for HD Careers fresher candidates.

The ledger records discovery observations, never publication or expiry decisions.
Use only on the website 'fresher' profile; personal job-search history is not
stored in this public repository. Missing candidates are NOT job closures.
"""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = 1


def empty_history():
    return {"schemaVersion": VERSION, "mode": "discovery_history_only",
            "lastRunAt": None, "boards": {}, "jobs": {}}


def board_key(provider, board, company):
    return "|".join((str(provider).casefold(), str(board).casefold(),
                     str(company).casefold()))


def update_history(existing, report):
    """Return (next_state, unseen_ids, seen_again_ids) without mutating inputs."""
    if not isinstance(existing, dict) or existing.get("schemaVersion") != VERSION:
        raise ValueError("Unknown history schema; never discard an old history")
    if existing.get("mode") != "discovery_history_only":
        raise ValueError("History mode must be read-only")
    if not isinstance(existing.get("jobs"), dict) or not isinstance(existing.get("boards"), dict):
        raise ValueError("History requires jobs/boards maps")
    if report.get("profile") != "fresher" or report.get("mode") != "shadow_only":
        raise ValueError("Website discovery history rejects personal search profiles")
    if report.get("publicationAllowed") is not False or report.get("expiryDecisionsAllowed") is not False:
        raise ValueError("History cannot accept publish/expiry-enabled reports")
    when = str(report.get("generatedAt") or "")
    try:
        timestamp = datetime.fromisoformat(when.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone aware")
    except (ValueError, TypeError) as e:
        raise ValueError("Invalid report generatedAt") from e
    previous = existing.get("lastRunAt")
    if previous:
        last = datetime.fromisoformat(previous.replace("Z", "+00:00"))
        if last.tzinfo is None or timestamp < last:
            raise ValueError("Out-of-order report: must not rewind persistent history")
    if not isinstance(report.get("scans"), list) or not isinstance(report.get("candidates"), list):
        raise ValueError("Scan/candidate arrays required")
    if report.get("candidateCount") != len(report["candidates"]) or report.get("scannedBoards") != len(report["scans"]):
        raise ValueError("Report count mismatch")

    new = deepcopy(existing)
    new["lastRunAt"] = when
    complete_keys = set()
    visited = set()
    for scan in report["scans"]:
        key = board_key(scan.get("provider"), scan.get("board"), scan.get("company"))
        if key in visited:
            raise ValueError("Duplicate scan board in report")
        visited.add(key)
        complete = scan.get("complete") is True and scan.get("status") == "ok"
        if complete:
            complete_keys.add(key)
        current = new["boards"].get(key, {})
        current.update({
            "company": str(scan.get("company") or ""), "provider": scan.get("provider"),
            "board": scan.get("board"), "lastAttemptAt": when,
            "lastAttemptStatus": "complete" if complete else "incomplete",
            "lastAttemptNotes": scan.get("notes", [])[:5],
            "lastReportedCandidates": scan.get("newReviewCandidates", 0),
        })
        if complete:
            current["lastCompleteAt"] = when
        new["boards"][key] = current

    newly_discovered, repeated, seen = [], [], set()
    for item in report["candidates"]:
        candidate_id = str(item.get("id") or "")
        if not candidate_id or candidate_id in seen:
            raise ValueError("Candidate ID missing or repeated")
        seen.add(candidate_id)
        src_key = board_key(item.get("sourceProvider"), item.get("sourceBoard"), item.get("company"))
        if src_key not in visited:
            raise ValueError("Candidate not associated with a scanned ATS board")
        if item.get("reviewedStatus") != "unreviewed" or item.get("eligibilityStatus") != "needs_manual_verification":
            raise ValueError("Only unreviewed candidates may enter history")
        if not item.get("apply") or not item.get("externalId") or not item.get("role"):
            raise ValueError("Candidate missing source identity")
        previous_item = new["jobs"].get(candidate_id)
        if previous_item:
            if (previous_item.get("provider") != item.get("sourceProvider")
                or previous_item.get("externalId") != str(item.get("externalId"))):
                raise ValueError("Candidate stable identifier collision")
            repeated.append(candidate_id)
            count = int(previous_item["seenCount"]) + 1
            first = previous_item["firstSeenAt"]
        else:
            newly_discovered.append(candidate_id)
            first, count = when, 1
        new["jobs"][candidate_id] = {
            "company": item["company"], "role": item["role"],
            "location": item.get("loc", ""), "apply": item["apply"],
            "provider": item["sourceProvider"], "board": item["sourceBoard"],
            "externalId": str(item["externalId"]), "boardKey": src_key,
            "firstSeenAt": first, "lastSeenAt": when, "seenCount": count,
            "observationStatus": "observed", "reviewState": "not_submitted",
            "eligibleForPublishing": False, "expired": False,
        }
    # A complete board did not list a previously selected candidate. Because the
    # candidate filter can change, that is *not* evidence of job expiry.
    for candidate_id, item in new["jobs"].items():
        if item["boardKey"] in complete_keys and candidate_id not in seen:
            item["observationStatus"] = "not_reobserved_needs_verification"
        # For a failed/partial/skipped board preserve the prior state unchanged.
    new["lastRunStats"] = {
        "scannedBoards": len(report["scans"]), "completeBoards": len(complete_keys),
        "newCandidates": len(newly_discovered), "repeatCandidates": len(repeated),
        "totalTracked": len(new["jobs"]),
        "noExpiryOrPublicationAuthority": True,
    }
    return new, newly_discovered, repeated


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--history", default=str(ROOT / "data/ats-discovery-history.json"))
    p.add_argument("--report", required=True)
    p.add_argument("--output", default="ats-discovery-history-next.json")
    p.add_argument("--new-output", default="ats-discovery-new-candidates.json")
    args = p.parse_args()
    original = Path(args.history)
    history = json.loads(original.read_text(encoding="utf-8")) if original.exists() else empty_history()
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    updated, new_ids, repeat_ids = update_history(history, report)
    Path(args.output).write_text(json.dumps(updated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    new_set = set(new_ids)
    new_items = [c for c in report["candidates"] if c["id"] in new_set]
    Path(args.new_output).write_text(json.dumps({
        "mode": "review_candidate_draft_only", "publicationAllowed": False,
        "expiryDecisionsAllowed": False, "profile": "fresher",
        "generatedAt": report["generatedAt"], "newCandidates": new_items,
        "newCount": len(new_items), "repeatCount": len(repeat_ids),
        "discoveredFor": "manual source validation before separate HD Careers Admin review",
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(updated["lastRunStats"], sort_keys=True))


if __name__ == "__main__":
    main()
