"""Rank existing job pages for source-backed editorial improvement without dropping jobs."""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER = re.compile(r"refer to (?:the )?official|review the official job|not specified|as per (?:the )?employer", re.I)


def words(value: str) -> int:
    return len(re.findall(r"\b[\w]+(?:[-'][\w]+)*\b", html.unescape(value or "")))


def evaluate(job: dict) -> dict:
    desc = str(job.get("desc") or "")
    eligibility = str(job.get("elig") or "")
    responsibilities = [str(x).strip() for x in job.get("resp", []) if str(x).strip()]
    skills = [str(x).strip() for x in job.get("skills", []) if str(x).strip()]
    content = " ".join([desc, eligibility, str(job.get("who") or ""), *responsibilities, *skills])
    word_count = words(content)
    desc_words = words(desc)
    flags = []
    if desc_words < 35:
        flags.append("employer-specific summary under 35 words")
    if word_count < 120:
        flags.append("very limited source-specific content")
    if len(responsibilities) < 3:
        flags.append("fewer than three sourced responsibilities")
    if PLACEHOLDER.search(eligibility):
        flags.append("eligibility needs official-source confirmation")
    if not skills:
        flags.append("no source-listed skills")
    if not str(job.get("sourceName") or "").strip():
        flags.append("source attribution missing")
    if not str(job.get("verifiedDate") or "").strip():
        flags.append("verification date missing")
    if not str(job.get("apply") or "").startswith("https://"):
        flags.append("missing HTTPS employer application")
    score = min(100, (35 if desc_words >= 70 else 20 if desc_words >= 35 else 5)
                + min(25, len(responsibilities) * 5)
                + min(20, len(skills) * 4)
                + (10 if eligibility and not PLACEHOLDER.search(eligibility) else 0)
                + (10 if str(job.get("sourceName") or "").strip() else 0))
    return {
        "id": job.get("id"), "company": job.get("company"), "role": job.get("role"),
        "officialUrl": job.get("apply"), "page": job.get("page"), "status": job.get("status"),
        "descriptionWords": desc_words, "sourceSpecificWords": word_count,
        "responsibilityCount": len(responsibilities), "qualityScore": score,
        "flags": flags,
        "editorialState": "needs_source_research" if flags else "reviewed_by_rule",
        "note": "Do not rewrite requirements from guesses; retain the listing and verify changes on the exact employer requisition."
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="docs/adsense-editorial-priorities.json")
    args = parser.parse_args()
    jobs = json.loads((ROOT / "data/jobs.json").read_text(encoding="utf-8"))
    records = [evaluate(job) for job in jobs]
    active = sorted((x for x in records if x["status"] == "active"),
                    key=lambda row: (row["qualityScore"], row["descriptionWords"], str(row["company"])))
    report = {
        "policy": "Do not expire, hide or invent content for short jobs. Resolve editorials using exact official links.",
        "total": len(records),
        "active": len(active),
        "activeUnder35Words": sum(x["descriptionWords"] < 35 for x in active),
        "activeNeedsResearch": sum(bool(x["flags"]) for x in active),
        "expiredRetained": sum(x["status"] == "expired" for x in records),
        "priorities": active,
    }
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"AdSense editorial priority report: {report['activeNeedsResearch']} of {report['active']} active jobs need source improvements. No jobs modified or hidden.")


if __name__ == "__main__":
    main()
