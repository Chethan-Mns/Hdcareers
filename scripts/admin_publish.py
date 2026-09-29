from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "jobs.json"

REQUIRED = [
    "page", "domain", "company", "salary", "logo", "role", "roleTag", "loc",
    "locationFilter", "batch", "elig", "cat", "expType", "expYears", "date",
    "desc", "resp", "apply", "status", "verifiedDate", "sourceName", "skills", "who", "workMode"
]
CATS = {"it", "internship", "apprenticeship", "campus", "remote", "walkin", "experienced", "govt"}
EXP_TYPES = {"fresher", "experienced"}


def normalize_url(value: str) -> str:
    text = str(value or "").strip()
    try:
        p = urlsplit(text)
        return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), p.query, ""))
    except Exception:
        return text.rstrip("/").lower()


def slugify(value: str) -> str:
    out = re.sub(r"[^a-z0-9]+", "-", str(value or "job").lower()).strip("-")
    return out[:80] or "job"


def validate(job: dict, pos: int) -> None:
    missing = [k for k in REQUIRED if k not in job]
    if missing:
        raise SystemExit(f"Job #{pos} missing fields: {', '.join(missing)}")
    if not str(job["company"]).strip() or not str(job["role"]).strip():
        raise SystemExit(f"Job #{pos} requires company and role")
    if job["cat"] not in CATS:
        raise SystemExit(f"Job #{pos} has unsupported category")
    if job["expType"] not in EXP_TYPES:
        raise SystemExit(f"Job #{pos} has unsupported experience type")
    if job["status"] not in {"active", "expired"}:
        raise SystemExit(f"Job #{pos} has unsupported status")
    if not isinstance(job["resp"], list) or not job["resp"]:
        raise SystemExit(f"Job #{pos} requires responsibilities")
    if not isinstance(job["skills"], list) or not job["skills"]:
        raise SystemExit(f"Job #{pos} requires skills")
    if not str(job["who"]).strip() or not str(job["sourceName"]).strip() or not str(job["verifiedDate"]).strip():
        raise SystemExit(f"Job #{pos} requires source, verification date and who-should-apply text")
    if not isinstance(job["logo"], list) or len(job["logo"]) != 2:
        raise SystemExit(f"Job #{pos} logo must be [initials, color]")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: admin_publish.py <github-event-path>")

    event = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    incoming = event.get("client_payload", {}).get("jobs", [])
    if not isinstance(incoming, list) or not incoming:
        raise SystemExit("No jobs supplied in repository_dispatch payload")
    if len(incoming) > 20:
        raise SystemExit("Maximum 20 jobs per deployment")

    current = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    if not isinstance(current, list):
        raise SystemExit("data/jobs.json must be an array")

    for pos, job in enumerate(incoming, start=1):
        if not isinstance(job, dict):
            raise SystemExit(f"Job #{pos} must be an object")
        validate(job, pos)

    existing_urls = {normalize_url(j.get("apply", "")) for j in current}
    existing_pairs = {(str(j.get("company", "")).lower(), str(j.get("role", "")).lower()) for j in current}
    batch_urls = set()
    batch_pairs = set()

    for job in incoming:
        url = normalize_url(job["apply"])
        pair = (str(job["company"]).lower(), str(job["role"]).lower())
        if url in existing_urls or url in batch_urls or pair in existing_pairs or pair in batch_pairs:
            raise SystemExit(f"Duplicate job: {job['company']} — {job['role']}")
        batch_urls.add(url)
        batch_pairs.add(pair)

    next_id = max([int(j.get("id", 0) or 0) for j in current] + [0]) + 1
    used_pages = {str(j.get("page", "")).lower() for j in current}

    prepared = []
    for raw in incoming:
        job = dict(raw)
        job["id"] = next_id
        next_id += 1

        requested = str(job.get("page", "")).strip()
        if not (requested.startswith("jobs/") and requested.endswith(".html") and ".." not in requested):
            requested = f"jobs/{slugify(job['company'] + '-' + job['role'])}.html"

        page = requested
        suffix = 2
        while page.lower() in used_pages:
            page = re.sub(r"\.html$", f"-{suffix}.html", requested)
            suffix += 1
        job["page"] = page
        used_pages.add(page.lower())
        prepared.append(job)

    DATA_FILE.write_text(json.dumps(prepared + current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(prepared)} job(s) for direct production publish")


if __name__ == "__main__":
    main()
