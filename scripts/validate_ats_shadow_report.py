#!/usr/bin/env python3
"""Fail-closed integration checks for real official-ATS extraction artifacts.

Reports are read-only; this script does not modify production website or queue.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from discovery_ats_shadow import (
    PERSONAL_PROFILE, boards_from_jobs, canonical, is_india, match_signal, parse_board,
)

REQUIRED = ("id", "company", "role", "loc", "apply", "externalId",
            "sourceProvider", "sourceBoard", "eligibilityStatus",
            "reviewedStatus", "searchProfile", "descriptionExcerpt")
SUPPORTED = {"greenhouse", "lever", "ashby", "smartrecruiters", "workday"}


def audit(report, existing_jobs):
    errors, warnings = [], []
    profile = report.get("profile", "fresher")
    if profile not in {"fresher", PERSONAL_PROFILE}:
        errors.append("Unsupported profile")
    if report.get("mode") != "shadow_only" or report.get("publicationAllowed") is not False:
        errors.append("Only non-publishing shadow reports accepted")
    if report.get("expiryDecisionsAllowed") is not False:
        errors.append("Shadow report must never expire listings")
    candidates, scans = report.get("candidates"), report.get("scans")
    if not isinstance(candidates, list) or not isinstance(scans, list):
        errors.append("Missing scans or candidate arrays")
        return {"passed": False, "errors": errors, "warnings": warnings}
    if len(scans) != report.get("scannedBoards") or len(candidates) != report.get("candidateCount"):
        errors.append("Report count mismatch")
    if report.get("totalSeedBoards", -1) < len(scans):
        errors.append("Scan count exceeds seeded boards")
    if any(s.get("status") not in {"ok", "error", "partial"} for s in scans):
        errors.append("Unknown scan status")
    if sum(not s.get("complete") for s in scans) != report.get("partialOrFailedBoards"):
        errors.append("Partial/failure count mismatch")
    for s in scans:
        if s.get("complete") and s.get("status") != "ok":
            errors.append("Only an ok scan can be complete")
        if not s.get("complete") and s.get("status") == "ok":
            errors.append("An incomplete scan was labeled ok")
    existing = {canonical(j.get("apply")) for j in existing_jobs if isinstance(j, dict)}
    seen_url, seen_id, seen_role = set(), set(), set()
    provider_counts, company_counts, category_counts = Counter(), Counter(), Counter()
    for idx, c in enumerate(candidates):
        missing = [k for k in REQUIRED if not str(c.get(k) or "").strip()]
        if missing:
            errors.append(f"Candidate {idx}: missing {','.join(missing)}")
            continue
        company, role, url = c["company"], c["role"], canonical(c["apply"])
        p = parse_board(company, url)
        if not p or p["provider"] != c["sourceProvider"] or p["board"].lower() != c["sourceBoard"].lower():
            errors.append(f"Candidate {idx}: official ATS board mismatch")
        if not is_india(c["loc"], c.get("countryEvidence", "")):
            errors.append(f"Candidate {idx}: lacks India location evidence")
        if c.get("reviewedStatus") != "unreviewed" or c.get("eligibilityStatus") != "needs_manual_verification":
            errors.append(f"Candidate {idx}: incorrectly authorized")
        if c.get("searchProfile") != profile:
            errors.append(f"Candidate {idx}: cross-profile contamination")
        if not match_signal(profile, role, c.get("descriptionForValidation") or c.get("descriptionExcerpt") or ""):
            errors.append(f"Candidate {idx}: failed role/profile signal")
        if profile == "fresher" and url in existing:
            errors.append(f"Candidate {idx}: duplicate already on site")
        rid = (c["sourceProvider"], c["sourceBoard"].lower(), str(c["externalId"]))
        rkey = (company.casefold().strip(), role.casefold().strip())
        if url in seen_url or rid in seen_id or rkey in seen_role:
            errors.append(f"Candidate {idx}: duplicate URL/ID/role")
        seen_url.add(url)
        seen_id.add(rid)
        seen_role.add(rkey)
        provider_counts[c["sourceProvider"]] += 1
        company_counts[company] += 1
        category_counts[c.get("categoryHint", "unknown")] += 1
    if any(s.get("status") != "ok" for s in scans):
        warnings.append("Partial or failed boards excluded from expiry evidence; scan is not exhaustive")
    if not candidates:
        warnings.append("No matching candidates; no conclusion about market demand")
    summary = {
        "passed": not errors,
        "profile": profile, "scannedBoards": len(scans),
        "candidateCount": len(candidates), "employers": len(company_counts),
        "partialOrFailedBoards": sum(not x.get("complete") for x in scans),
        "providerCandidateCounts": dict(provider_counts),
        "categoryCandidateCounts": dict(category_counts),
        "errors": errors[:30], "warnings": warnings,
        "productionMutationsAllowed": False,
    }
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--jobs", default=str(Path(__file__).resolve().parents[1] / "data/jobs.json"))
    ap.add_argument("--summary", default="")
    args = ap.parse_args()
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    jobs = json.loads(Path(args.jobs).read_text(encoding="utf-8"))
    result = audit(report, jobs)
    if args.summary:
        Path(args.summary).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
