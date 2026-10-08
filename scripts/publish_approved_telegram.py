from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from check_job_availability import require_active
from post_telegram import SITE_BASE, load_current_jobs, message_for, send_telegram
from publish_verified_telegram import live_job

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "telegram-approved-batch.json"
LEDGER = ROOT / "data" / "telegram-deliveries.json"
MAX_PAGES = 20


def load_json(path, default):
    if not path.exists():
        return default
    data = json.loads(path.read_text(encoding="utf-8"))
    if type(data) is not type(default):
        raise SystemExit(f"Unexpected JSON type in {path.name}")
    return data


def save_ledger(ledger):
    LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def requested_pages():
    manual = os.getenv("JOB_PAGES", "").strip()
    if manual:
        pages = [p.strip().lstrip("/") for p in manual.split(",") if p.strip()]
        batch = "manual-approved-" + os.getenv("GITHUB_RUN_ID", "local")
    else:
        manifest = load_json(MANIFEST, {})
        if manifest.get("approved") is not True or not str(manifest.get("batchId", "")).strip():
            raise SystemExit("Approval required: a batchId and approved=true are missing")
        batch = str(manifest["batchId"])
        pages = manifest.get("pages", [])
    if not isinstance(pages, list) or not 1 <= len(pages) <= MAX_PAGES or len(set(pages)) != len(pages):
        raise SystemExit("Expected 1-20 unique approved pages")
    if any(not isinstance(p, str) or not p.startswith("jobs/") or not p.endswith(".html") or ".." in p for p in pages):
        raise SystemExit("Invalid approved job page path")
    return batch, pages


def wait_for_exact_page(job, max_seconds=300):
    deadline = time.monotonic() + max_seconds
    while time.monotonic() < deadline:
        if live_job(job):
            return True
        time.sleep(10)
    return False


def publish():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    channel = os.getenv("TELEGRAM_CHANNEL_ID", "").strip() or os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not channel:
        raise SystemExit("Telegram delivery failed: GitHub Telegram secrets are missing")
    batch_id, pages = requested_pages()
    jobs = {str(j.get("page", "")).strip().lstrip("/"): j for j in load_current_jobs()}
    ledger = load_json(LEDGER, {})
    pending = []
    for page in pages:
        job = jobs.get(page)
        if not job:
            raise SystemExit("Approved job missing from data/jobs.json: " + page)
        key = f"{channel}|{page}"
        prior = ledger.get(key, {})
        if prior.get("status") == "delivered":
            print("ALREADY DELIVERED (skipped):", page, "messageId:", prior.get("messageId"))
            continue
        if prior.get("status") == "uncertain":
            raise SystemExit("Delivery outcome uncertain; review channel before retry: " + page)
        if job.get("status") != "active":
            raise SystemExit("Approved job is not active: " + page)
        pending.append((page, job, key))
    if not pending:
        print("All approved pages already delivered; no Telegram messages sent")
        return
    print(f"APPROVED BATCH {batch_id}: {len(pending)} pending of {len(pages)} pages")
    for page, job, key in pending:
        require_active(job)
        if not wait_for_exact_page(job):
            raise SystemExit("Website deployment not verified; nothing sent: " + SITE_BASE + page)
        print("Verified deployed page:", page)
    for page, job, key in pending:
        try:
            message_id = send_telegram(token, channel, message_for(job))
        except Exception as exc:
            uncertain = not (isinstance(exc, RuntimeError) and str(exc).startswith("Telegram HTTP "))
            ledger[key] = {
                "status": "uncertain" if uncertain else "failed",
                "batchId": batch_id,
                "page": page,
                "checkedAt": datetime.now(timezone.utc).isoformat(),
                "reason": type(exc).__name__,
            }
            save_ledger(ledger)
            raise
        ledger[key] = {
            "status": "delivered",
            "batchId": batch_id,
            "page": page,
            "channel": channel,
            "messageId": message_id,
            "deliveredAt": datetime.now(timezone.utc).isoformat(),
        }
        save_ledger(ledger)
        print("DELIVERED:", page, "messageId:", message_id)
    print(f"BATCH {batch_id} delivered: {len(pending)} new messages")


if __name__ == "__main__":
    publish()
