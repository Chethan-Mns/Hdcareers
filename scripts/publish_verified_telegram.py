from __future__ import annotations

import json
import html
import re
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen

from check_job_availability import require_active
from post_telegram import load_current_jobs, message_for, send_telegram

BASE = "https://hdcareers.in/"
ROOT = Path(__file__).resolve().parents[1]


def live_job(job: dict) -> bool:
    page = str(job.get("page", "")).strip().lstrip("/")
    if not page.startswith("jobs/") or not page.endswith(".html"):
        return False
    try:
        req = Request(BASE + page, headers={"User-Agent": "HD-Careers-Publisher/1.0"})
        with urlopen(req, timeout=20) as response:
            if response.status != 200:
                return False
            body = response.read(400000).decode("utf-8", errors="replace").lower()
        title_match = re.search(r"<title[^>]*>(.*?)</title>", body, flags=re.I | re.S)
        title = html.unescape(title_match.group(1)) if title_match else ""
        company = str(job.get("company", "")).lower().strip()
        role = str(job.get("role", "")).lower().strip()
        canonical = BASE + page
        return (
            "<html" in body
            and "jobposting" in body
            and bool(company and company in title)
            and bool(role and role in title)
            and ('href="' + canonical.lower() + '"') in body
        )
    except Exception:
        return False


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    channel = os.getenv("TELEGRAM_CHANNEL_ID", "").strip() or os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not channel:
        raise SystemExit("Telegram bot token or channel ID missing from GitHub secrets")
    requested = [x.strip().lstrip("/") for x in os.getenv("JOB_PAGES", "").split(",") if x.strip()]
    if not requested or len(requested) > 20 or len(set(requested)) != len(requested):
        raise SystemExit("Provide 1-20 unique job page paths")
    jobs = {str(j.get("page", "")).lstrip("/"): j for j in load_current_jobs()}
    for page in requested:
        job = jobs.get(page)
        if not job:
            raise SystemExit("Job is missing from data/jobs.json: " + page)
        if not live_job(job):
            raise SystemExit("Live job page missing or invalid: " + page)
        require_active(job)
    for page in requested:
        job = jobs[page]
        send_telegram(token, channel, message_for(job))
        print("Posted:", page)


if __name__ == "__main__":
    main()
