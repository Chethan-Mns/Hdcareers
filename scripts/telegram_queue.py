from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from check_job_availability import require_active
from post_telegram import DATA_FILE, message_for, send_telegram, wait_for_live

ROOT = Path(__file__).resolve().parents[1]
QUEUE_FILE = ROOT / "data" / "telegram-queue.json"


def key(job: dict) -> str:
    return str(job.get("id") or job.get("page") or job.get("apply") or f"{job.get('company')}|{job.get('role')}")


def load_queue() -> dict:
    if not QUEUE_FILE.exists():
        return {"pending": [], "posted": []}
    data = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {"pending": [], "posted": []}


def save_queue(data: dict) -> None:
    QUEUE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def old_jobs(before: str) -> list[dict]:
    if not before or set(before) == {"0"}:
        return []
    result = subprocess.run(["git", "show", f"{before}:data/jobs.json"], cwd=ROOT, text=True, capture_output=True)
    if result.returncode != 0:
        return []
    try:
        data = json.loads(result.stdout)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def enqueue(before: str) -> None:
    current = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    old = old_jobs(before)
    old_keys = {key(j) for j in old}
    q = load_queue()
    known = {str(x.get("key")) for x in q.get("pending", []) + q.get("posted", [])}
    added = []
    for job in current:
        k = key(job)
        if k not in old_keys and k not in known:
            q.setdefault("pending", []).append({
                "key": k,
                "job_id": job.get("id"),
                "company": job.get("company"),
                "role": job.get("role"),
                "page": job.get("page"),
                "queued_at": datetime.now(timezone.utc).isoformat(),
            })
            added.append(k)
    save_queue(q)
    print(f"Queued {len(added)} job(s) for hourly Telegram publishing.")


def publish_one() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    channel = os.environ.get("TELEGRAM_CHANNEL_ID", "").strip()
    if not token or not channel:
        raise SystemExit("Telegram secrets are not configured.")

    q = load_queue()
    pending = q.get("pending", [])
    if not pending:
        print("Telegram queue is empty.")
        return

    jobs = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    by_key = {key(j): j for j in jobs}
    item = pending[0]
    job = by_key.get(str(item.get("key")))
    if not job:
        item["status"] = "missing"
        item["finished_at"] = datetime.now(timezone.utc).isoformat()
        q.setdefault("posted", []).append(item)
        q["pending"] = pending[1:]
        save_queue(q)
        print("Skipped missing queued job.")
        return

    require_active(job)
    if not wait_for_live(str(job.get("page", ""))):
        raise SystemExit("Job page is not live; keeping it queued for retry.")

    send_telegram(token, channel, message_for(job))
    item["status"] = "posted"
    item["posted_at"] = datetime.now(timezone.utc).isoformat()
    q.setdefault("posted", []).append(item)
    q["pending"] = pending[1:]
    save_queue(q)
    print(f"Posted to Telegram: {job.get('company')} — {job.get('role')}")


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in {"enqueue", "publish-one"}:
        raise SystemExit("Usage: telegram_queue.py enqueue <before-sha> | publish-one")
    if sys.argv[1] == "enqueue":
        if len(sys.argv) != 3:
            raise SystemExit("Usage: telegram_queue.py enqueue <before-sha>")
        enqueue(sys.argv[2])
    else:
        publish_one()


if __name__ == "__main__":
    main()
