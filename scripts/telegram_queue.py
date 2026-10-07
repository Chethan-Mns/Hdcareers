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


def added_jobs(before: str) -> list[dict]:
    current = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    old = old_jobs(before)
    old_by_key = {key(j): j for j in old}
    selected = []
    for job in current:
        k = key(job)
        previous = old_by_key.get(k)
        if previous is None:
            selected.append(job)
            continue
        request = str(job.get("manualPublishRequestedAt", "") or "").strip()
        old_request = str(previous.get("manualPublishRequestedAt", "") or "").strip()
        if request and request != old_request:
            selected.append(job)
    return selected


def enqueue(before: str) -> None:
    q = load_queue()
    known = {str(x.get("key")) for x in q.get("pending", []) + q.get("posted", [])}
    added = []
    for job in added_jobs(before):
        k = key(job)
        if k not in known:
            q.setdefault("pending", []).append({
                "key": k, "job_id": job.get("id"), "company": job.get("company"),
                "role": job.get("role"), "page": job.get("page"),
                "queued_at": datetime.now(timezone.utc).isoformat(),
            })
            added.append(k)
    save_queue(q)
    print(f"Queued {len(added)} job(s) for hourly Telegram publishing.")


def telegram_credentials() -> tuple[str, str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    channel = os.environ.get("TELEGRAM_CHANNEL_ID", "").strip() or os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not channel:
        raise SystemExit("Telegram secrets are not configured.")
    return token, channel


def mark_posted(q: dict, item: dict) -> None:
    item["status"] = "posted"
    item["posted_at"] = datetime.now(timezone.utc).isoformat()
    q.setdefault("posted", []).append(item)
    q["pending"] = [x for x in q.get("pending", []) if str(x.get("key")) != str(item.get("key"))]


def publish_job(job: dict, q: dict, token: str, channel: str) -> bool:
    k = key(job)
    if any(str(x.get("key")) == k for x in q.get("posted", [])):
        print(f"Already posted to Telegram: {job.get('company')} — {job.get('role')}")
        return True
    require_active(job)
    if not wait_for_live(str(job.get("page", ""))):
        return False
    send_telegram(token, channel, message_for(job))
    item = next((x for x in q.get("pending", []) if str(x.get("key")) == k), {
        "key": k, "job_id": job.get("id"), "company": job.get("company"),
        "role": job.get("role"), "page": job.get("page"),
    })
    mark_posted(q, item)
    save_queue(q)
    print(f"Posted to Telegram: {job.get('company')} — {job.get('role')}")
    return True


def publish_new(before: str) -> None:
    token, channel = telegram_credentials()
    q = load_queue()
    jobs = added_jobs(before)
    if not jobs:
        print("No newly added jobs found.")
        return
    failed = []
    for job in jobs:
        try:
            if not publish_job(job, q, token, channel):
                failed.append(str(job.get("id")))
        except Exception as exc:
            failed.append(str(job.get("id")))
            print(f"Telegram publish failed for job {job.get('id')}: {exc}")
    if failed:
        raise SystemExit("Telegram publish failed for job(s): " + ", ".join(failed))


def publish_one() -> None:
    token, channel = telegram_credentials()
    q = load_queue()
    jobs = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    by_key = {key(j): j for j in jobs}

    for item in list(q.get("pending", [])):
        job = by_key.get(str(item.get("key")))
        if not job:
            item["status"] = "missing"
            item["finished_at"] = datetime.now(timezone.utc).isoformat()
            q.setdefault("posted", []).append(item)
            q["pending"] = [x for x in q.get("pending", []) if str(x.get("key")) != str(item.get("key"))]
            save_queue(q)
            continue
        try:
            if publish_job(job, q, token, channel):
                return
        except Exception as exc:
            item["last_error"] = str(exc)[:500]
            item["last_attempt_at"] = datetime.now(timezone.utc).isoformat()
            save_queue(q)
            print(f"Skipping queued job {item.get('key')} this run: {exc}")
            continue

    print("No publishable Telegram job found in queue.")



def publish_all() -> None:
    token, channel = telegram_credentials()
    q = load_queue()
    jobs = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    by_key = {key(j): j for j in jobs}
    failed = []

    for item in list(q.get("pending", [])):
        job = by_key.get(str(item.get("key")))
        if not job:
            item["status"] = "missing"
            item["finished_at"] = datetime.now(timezone.utc).isoformat()
            q.setdefault("posted", []).append(item)
            q["pending"] = [x for x in q.get("pending", []) if str(x.get("key")) != str(item.get("key"))]
            save_queue(q)
            continue
        try:
            if not publish_job(job, q, token, channel):
                failed.append(str(item.get("key")))
        except Exception as exc:
            item["last_error"] = str(exc)[:500]
            item["last_attempt_at"] = datetime.now(timezone.utc).isoformat()
            save_queue(q)
            failed.append(str(item.get("key")))
            print(f"Telegram publish failed for queued job {item.get('key')}: {exc}")

    if failed:
        raise SystemExit("Telegram catch-up failed for job(s): " + ", ".join(failed))
    print("Published all pending Telegram jobs.")



def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in {"enqueue", "publish-one", "publish-new", "publish-all"}:
        raise SystemExit("Usage: telegram_queue.py enqueue <before-sha> | publish-new <before-sha> | publish-one | publish-all")
    if sys.argv[1] in {"enqueue", "publish-new"}:
        if len(sys.argv) != 3:
            raise SystemExit(f"Usage: telegram_queue.py {sys.argv[1]} <before-sha>")
        globals()[sys.argv[1].replace("-", "_")](sys.argv[2])
    elif sys.argv[1] == "publish-one":
        publish_one()
    else:
        publish_all()


if __name__ == "__main__":
    main()
