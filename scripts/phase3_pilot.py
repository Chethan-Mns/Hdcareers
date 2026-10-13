"""Phase 3: single-employer Lever pilot, strictly read-only.

Discover -> exact employer confirmation -> source-grounded draft -> release gate.
Does not modify job data, create GitHub deployments, or contact Telegram.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_job_availability import check, fetch_json

EMPLOYER = "AHEAD"
SITE = "thinkahead"
LIST_URL = f"https://api.lever.co/v0/postings/{SITE}?mode=json&limit=12"
POSTING_URL = f"https://jobs.lever.co/{SITE}/"
OUTPUT = ROOT / "phase3-pilot-report.json"
MAX_CANDIDATES = 12


def source_candidate(raw):
    if not isinstance(raw, dict):
        return None
    posting_id = str(raw.get("id") or "").strip()
    if not re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,36}", posting_id):
        return None
    url = str(raw.get("hostedUrl") or "").strip()
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "jobs.lever.co" or parsed.path.rstrip("/") != f"/{SITE}/{posting_id}":
        return None
    title = str(raw.get("text") or "").strip()
    if len(title) < 6 or len(title) > 200:
        return None
    return {"id": posting_id, "company": EMPLOYER, "role": title, "apply": url}


def source_grounded_draft(candidate, exact):
    """No embellished descriptions, salaries, degrees or fabricated dates."""
    if not isinstance(exact, dict) or str(exact.get("id")) != candidate["id"]:
        return {"state": "hold", "reasons": ["exact-source-identity"], "facts": {}}
    if str(exact.get("text") or "").strip().casefold() != candidate["role"].casefold():
        return {"state": "hold", "reasons": ["exact-source-title"], "facts": {}}
    if exact.get("hostedUrl", "").rstrip("/") != candidate["apply"].rstrip("/"):
        return {"state": "hold", "reasons": ["exact-source-url"], "facts": {}}
    categories = exact.get("categories") if isinstance(exact.get("categories"), dict) else {}
    location = str(categories.get("location") or "").strip()
    description = re.sub(r"\s+", " ", str(exact.get("descriptionPlain") or "").strip())[:6000]
    sections = exact.get("lists") if isinstance(exact.get("lists"), list) else []
    duties = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        heading = re.sub(r"<[^>]+>", "", str(section.get("text") or ""))
        text = re.sub(r"<[^>]+>", " ", str(section.get("content") or ""))
        body = re.sub(r"\s+", " ", text).strip()
        if heading and body:
            duties.append({"heading": heading[:100], "text": body[:2000]})
    reasons = []
    if not description:
        reasons.append("missing-employer-description")
    if not location:
        reasons.append("missing-employer-location")
    if not duties:
        reasons.append("missing-employer-requirements-or-duties")
    return {"state": "draft_ready" if not reasons else "hold", "reasons": reasons, "facts": {
        "company": candidate["company"], "role": candidate["role"], "apply": candidate["apply"],
        "location": location, "description": description, "sections": duties,
        "employerPostedAt": None, "salary": None, "experienceYears": None,
        "sourceProvider": "Lever", "sourcePostingId": candidate["id"]
    }}


def build_report(feed, published, fetch=fetch_json, verify=check, now=None):
    now = now or datetime.now(timezone.utc)
    if not isinstance(feed, list):
        raise ValueError("Incomplete or unexpected employer feed")
    output = {"mode": "shadow_only", "pilotEmployer": EMPLOYER, "source": LIST_URL,
              "checkedAt": now.isoformat(), "productionWrites": False,
              "websiteDeployments": 0, "telegramMessagesSent": 0,
              "autoPublishEnabled": False, "candidates": [], "summary": {}}
    existing = {str(j.get("apply") or "").rstrip("/") for j in published}
    seen = set()
    skipped = 0
    for raw in feed:
        candidate = source_candidate(raw)
        if not candidate or candidate["apply"] in seen:
            skipped += 1
            continue
        seen.add(candidate["apply"])
        if candidate["apply"].rstrip("/") in existing:
            skipped += 1
            continue
        if len(output["candidates"]) >= MAX_CANDIDATES:
            break
        record = {**candidate, "verification": "review", "draftState": "hold",
                  "reasons": [], "evidence": [], "readyForDraftReview": False, "readyForPublishing": False}
        try:
            exact = fetch(f"https://api.lever.co/v0/postings/{SITE}/{candidate['id']}")
            verified = verify({**candidate, "status": "active"}, now=now)
            if verified.get("state") != "active" or not str(verified.get("reason", "")).startswith("Lever public posting inventory contains the exact published job"):
                record["reasons"].append("not-independently-confirmed-live")
            elif verified.get("url") != candidate["apply"] or verified.get("id") != candidate["id"]:
                record["reasons"].append("verification-identity-mismatch")
            else:
                draft = source_grounded_draft(candidate, exact)
                record["verification"] = "active"
                record["draftState"] = draft["state"]
                record["reasons"].extend(draft["reasons"])
                record["facts"] = draft["facts"]
                record["evidence"] = ["exact-Lever-ID", "matching-source-title", "exact-official-URL", "fresh-Live-result"]
                record["readyForDraftReview"] = draft["state"] == "draft_ready"
                record["readyForPublishing"] = False  # Full published-job fields and independent deployment gate are not complete.
        except Exception as exc:
            record["reasons"].append("source-check-inconclusive:" + type(exc).__name__)
        output["candidates"].append(record)
    output["summary"] = {
        "sourceItems": len(feed), "newCandidatesChecked": len(output["candidates"]),
        "held": sum(not item["readyForDraftReview"] for item in output["candidates"]),
        "draftReady": sum(item["readyForDraftReview"] for item in output["candidates"]),
        "publishReady": 0,
        "existingOrInvalidSkipped": skipped
    }
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    jobs = json.loads((ROOT / "data" / "jobs.json").read_text(encoding="utf-8"))
    try:
        feed = fetch_json(LIST_URL)
        report = build_report(feed, jobs)
    except Exception as exc:
        report = {"mode": "shadow_only", "pilotEmployer": EMPLOYER, "source": LIST_URL,
                  "checkedAt": datetime.now(timezone.utc).isoformat(), "productionWrites": False,
                  "websiteDeployments": 0, "telegramMessagesSent": 0,
                  "autoPublishEnabled": False, "summary": {"error": type(exc).__name__, "detail": str(exc)[:220]},
                  "candidates": []}
    Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    assert report["mode"] == "shadow_only" and report["autoPublishEnabled"] is False
    if report["summary"].get("error"):
        raise SystemExit("Pilot source blocked: " + str(report["summary"]["error"]))


if __name__ == "__main__":
    main()
