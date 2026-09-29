"""Create a lightweight quality report for published job pages."""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER = re.compile(r"review the official job (?:posting|description)|details are not specified", re.I)


def words(value: str) -> int:
    return len(re.findall(r"\b[\w]+(?:[-'][\w]+)*\b", html.unescape(value or "")))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="content-quality-report.json")
    args = parser.parse_args()
    jobs = json.loads((ROOT / "data/jobs.json").read_text(encoding="utf-8"))
    rows = []
    for job in jobs:
        meaningful = " ".join([
            str(job.get("company", "")), str(job.get("role", "")), str(job.get("desc", "")),
            str(job.get("elig", "")), str(job.get("who", "")),
            " ".join(map(str, job.get("skills", []))), " ".join(map(str, job.get("resp", []))),
        ])
        flags = []
        if words(meaningful) < 180:
            flags.append("short job-specific content")
        if PLACEHOLDER.search(meaningful):
            flags.append("placeholder wording")
        for key in ("desc", "elig", "who", "sourceName", "verifiedDate", "workMode"):
            if not str(job.get(key, "")).strip():
                flags.append(f"missing {key}")
        if not job.get("skills"):
            flags.append("missing skills")
        rows.append({"id": job.get("id"), "company": job.get("company"), "role": job.get("role"),
                     "status": job.get("status"), "wordCount": words(meaningful), "flags": flags})
    output = ROOT / args.output
    output.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    flagged = sum(bool(row["flags"]) for row in rows)
    print(f"Content quality report: {flagged} of {len(rows)} listings flagged for review")


if __name__ == "__main__":
    main()
