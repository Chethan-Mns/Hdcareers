from __future__ import annotations

import json
from check_job_availability import require_active
import os
import subprocess
import sys
from pathlib import Path

from post_telegram import DATA_FILE, message_for, send_telegram, wait_for_live

ROOT = Path(__file__).resolve().parents[1]


def normalize_url(value: str) -> str:
    return str(value or "").strip().rstrip("/").lower()


def load_old_jobs(before: str) -> list[dict]:
    if not before or set(before) == {"0"}:
        return []
    result = subprocess.run(
        ["git", "show", f"{before}:data/jobs.json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []
    try:
        data = json.loads(result.stdout)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: post_telegram_from_push.py <before-sha>")

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    channel = os.environ.get("TELEGRAM_CHANNEL_ID", "").strip() or os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not channel:
        print("Telegram secrets are not configured in GitHub Actions. Skipping channel post.")
        return

    current = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    old = load_old_jobs(sys.argv[1])

    old_urls = {normalize_url(j.get("apply", "")) for j in old}
    old_pairs = {
        (str(j.get("company", "")).strip().lower(), str(j.get("role", "")).strip().lower())
        for j in old
    }

    added = []
    for job in current:
        url = normalize_url(job.get("apply", ""))
        pair = (str(job.get("company", "")).strip().lower(), str(job.get("role", "")).strip().lower())
        if url not in old_urls and pair not in old_pairs:
            added.append(job)

    if not added:
        print("No newly added jobs found.")
        return

    first_page = str(added[0].get("page", "") or "")
    if not wait_for_live(first_page):
        raise SystemExit("HD Careers page did not become live in time. Telegram post skipped.")

    for job in added:
        require_active(job)
        if not wait_for_live(str(job.get("page", ""))):
            raise SystemExit("Job page is not live; sharing stopped")
        send_telegram(token, channel, message_for(job))
        print(f"Posted to Telegram: {job.get('company')} — {job.get('role')}")


if __name__ == "__main__":
    main()
