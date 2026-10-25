"""Deployment-gated Telegram batch publisher: first message immediately, then hourly.

One confirmed message per batch per hour. GitHub cron is only a best-effort
wake-up mechanism; dueAt is anchored to the *actual* Telegram receipt.
Uncertain sends are never automatically retried.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data" / "telegram-hourly-queue.json"
LEDGER = ROOT / "data" / "telegram-deliveries.json"
MANIFEST = ROOT / "data" / "telegram-approved-batch.json"
JOBS = ROOT / "data" / "jobs.json"
INTERVAL = timedelta(hours=1)
DONE = {"delivered", "already-delivered"}
OPEN = {"pending", "sending", "uncertain"}


def load(path, fallback):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)


def stamp(value=None):
    return (value or datetime.now(timezone.utc)).isoformat()


def output(name, value):
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as file:
            file.write(f"{name}={value}\n")


def queue():
    value = load(QUEUE, {"version": 1, "intervalMinutes": 60, "items": []})
    if (not isinstance(value, dict) or value.get("version") != 1
            or value.get("intervalMinutes") != 60 or not isinstance(value.get("items"), list)):
        raise ValueError("Unexpected hourly queue format")
    if len({x.get("page") for x in value["items"]}) != len(value["items"]):
        raise ValueError("Duplicate page in Telegram queue")
    return value


def approved_batch():
    manifest = load(MANIFEST, {})
    batch_id = "admin-" + str(os.getenv("GITHUB_RUN_ID", ""))
    if not os.getenv("GITHUB_RUN_ID") or not manifest.get("approved") or manifest.get("batchId") != batch_id:
        return None, []
    pages = manifest.get("pages", [])
    if not isinstance(pages, list) or len(pages) > 20 or len(pages) != len(set(pages)):
        raise ValueError("Expected 1-20 unique approved pages")
    return batch_id, pages


def enqueue(event_path):
    event = load(Path(event_path), {})
    batch_id, pages = approved_batch()
    mode = event.get("client_payload", {}).get("telegramDeliveryMode", "")
    hourly = len(pages) > 1 or mode == "hourly"
    if not hourly or not pages:
        print("One-off VIP or no verified pages: use immediate Telegram sender")
        output("deferred", "false")
        return
    valid_pages = {j.get("page") for j in load(JOBS, []) if j.get("status", "active") == "active"}
    q = queue()
    ledger = load(LEDGER, {})
    known = {x["page"] for x in q["items"]}
    added = []
    now = stamp()
    for page in pages:
        if not isinstance(page, str) or not page.startswith("jobs/") or not page.endswith(".html") or page not in valid_pages:
            raise ValueError("Approved page missing from verified website job data: " + str(page))
        if page in known or any(v.get("page") == page and v.get("status") == "delivered" for v in ledger.values()):
            continue
        q["items"].append({"page": page, "batchId": batch_id, "status": "pending", "queuedAt": now})
        known.add(page)
        added.append(page)
    if added:
        save(QUEUE, q)
    print("Queued", len(added), "verified pages for immediate-first hourly delivery:", added)
    output("deferred", "true" if added else "false")


def reconcile(q, ledger):
    """Recover confirmed sends without treating an ambiguous claimed send as safe."""
    for item in q["items"]:
        if item.get("status") not in {"pending", "sending"}:
            continue
        entry = next((x for x in ledger.values()
                      if x.get("page") == item.get("page") and x.get("status") == "delivered"), None)
        if entry:
            item.update(status="already-delivered", deliveredAt=entry["deliveredAt"], messageId=entry["messageId"])
            item.pop("dueAt", None)


def refresh_due(q):
    """Schedule next items from confirmed Telegram receipts, not from a cron tick."""
    batches = {x.get("batchId") or "__legacy" for x in q["items"]}
    for batch_id in batches:
        members = [x for x in q["items"] if (x.get("batchId") or "__legacy") == batch_id]
        last = [parse(x["deliveredAt"]) for x in members
                if x.get("status") in DONE and x.get("deliveredAt")]
        if not last:
            for item in members:
                if item.get("status") == "pending":
                    item["dueAt"] = item.get("queuedAt") or stamp(datetime.now(timezone.utc) - timedelta(seconds=1))
            continue
        base = max(last)
        position = 0
        for item in members:
            if item.get("status") == "pending":
                position += 1
                item["dueAt"] = stamp(base + INTERVAL * position)


def claim(prime=False, now=None):
    q = queue()
    ledger = load(LEDGER, {})
    run_id = str(os.getenv("GITHUB_RUN_ID", "")).strip()
    if not run_id:
        raise ValueError("GITHUB_RUN_ID is required for unique at-most-once claims")
    reconcile(q, ledger)
    refresh_due(q)
    if any(x.get("status") == "sending" for x in q["items"]):
        # A sender whose result is uncommitted must be reconciled, not resent.
        save(QUEUE, q)
        print("Unresolved sending claim; holding to prevent duplicates")
        output("claimed", "false")
        return
    now = now or datetime.now(timezone.utc)
    chosen = None
    if prime:
        batch_id, approved = approved_batch()
        candidates = [x for x in q["items"] if x.get("batchId") == batch_id and x.get("page") in approved]
        if batch_id and not any(x.get("status") in DONE | {"uncertain"} for x in candidates):
            chosen = next((x for x in candidates if x.get("status") == "pending"), None)
    else:
        candidates = []
        blocked_batches = {x.get("batchId") for x in q["items"] if x.get("status") == "uncertain"}
        for item in q["items"]:
            if item.get("status") != "pending" or item.get("batchId") in blocked_batches:
                continue
            due = parse(item["dueAt"]) if item.get("dueAt") else (parse(item["queuedAt"]) if item.get("queuedAt") else now - timedelta(seconds=1))
            if due <= now:
                candidates.append((due, item))
        if candidates:
            chosen = min(candidates, key=lambda entry: entry[0])[1]
    if not chosen:
        save(QUEUE, q)
        future = [x.get("dueAt") for x in q["items"] if x.get("status") == "pending"]
        print("No eligible Telegram item; next due:", min((x for x in future if x), default="none"))
        output("claimed", "false")
        return
    chosen.update(status="sending", claimId=run_id, claimedAt=stamp(now))
    save(QUEUE, q)
    output("claimed", "true")
    output("page", chosen["page"])
    print("Claimed exactly one approved job:", chosen["page"], "due:", chosen.get("dueAt"))


def send():
    run = str(os.getenv("GITHUB_RUN_ID", "")).strip()
    q = queue()
    item = next((x for x in q["items"] if x.get("status") == "sending" and x.get("claimId") == run), None)
    if not item:
        raise ValueError("No pre-persisted Telegram claim owned by this run")
    page = item["page"]
    os.environ["JOB_PAGES"] = page
    try:
        from publish_approved_telegram import publish
        publish()
        ledger = load(LEDGER, {})
        receipt = next((v for v in ledger.values() if v.get("page") == page and v.get("status") == "delivered"), None)
        if not receipt or not isinstance(receipt.get("messageId"), int):
            raise RuntimeError("Telegram returned no durable message ID")
        item.update(status="delivered", messageId=receipt["messageId"],
                    deliveredAt=receipt.get("deliveredAt") or stamp())
        item.pop("dueAt", None)
        refresh_due(q)
        print("Telegram confirmed:", page, "message ID:", item["messageId"])
    except Exception as exc:
        # This may have failed after the Telegram server accepted the post.
        # Never silently retry an ambiguous outcome.
        item.update(status="uncertain", lastError=str(exc)[:360], failedAt=stamp())
        print("Telegram status requires manual reconciliation:", page, str(exc), file=sys.stderr)
        save(QUEUE, q)
        raise
    save(QUEUE, q)


def next_wakeup(now=None):
    """Compute a durable one-shot wake-up without modifying delivery data.

    GitHub cron can silently skip several hours. A dedicated short-lived chain
    job sleeps until the actual receipt-based dueAt and dispatches the sender.
    Uncertain or in-flight delivery must NEVER be awakened into a second send.
    """
    q = queue()
    ledger = load(LEDGER, {})
    reconcile(q, ledger)
    refresh_due(q)
    if any(x.get("status") == "sending" for x in q["items"]):
        print("Not arming relay: unresolved in-flight claim needs reconciliation")
        output("armed", "false")
        return
    blocked = {x.get("batchId") for x in q["items"] if x.get("status") == "uncertain"}
    pending = [x for x in q["items"] if x.get("status") == "pending"
               and x.get("batchId") not in blocked]
    if not pending:
        print("No eligible pending jobs; relay stops until next approved batch")
        output("armed", "false")
        return
    now = now or datetime.now(timezone.utc)
    next_due = min(parse(x.get("dueAt") or x.get("queuedAt") or stamp(now))
                   for x in pending)
    # Always re-read the queue in the dispatched workflow; a cron or new batch
    # may already have processed the selected page while this runner sleeps.
    seconds = max(0, int((next_due - now).total_seconds() + 0.999999))
    seconds = min(seconds, 3600)
    print("Arming next Telegram relay in", seconds, "seconds; next target:", stamp(next_due))
    output("armed", "true")
    output("delay_seconds", str(seconds))
    output("next_due", stamp(next_due))

def merge(snapshot_path):
    """Merge local sender state into fresh main after website/other run updates."""
    current = queue()
    captured = load(Path(snapshot_path), {})
    if not isinstance(captured, dict) or not isinstance(captured.get("items"), list):
        raise ValueError("Invalid queue snapshot")
    by_page = {x["page"]: x for x in current["items"]}
    rank = {"pending": 1, "sending": 2, "uncertain": 3, "already-delivered": 4, "delivered": 4}
    for item in captured["items"]:
        page = item.get("page")
        if not isinstance(page, str) or page not in by_page:
            if not isinstance(page, str):
                raise ValueError("Invalid snapshot page")
            current["items"].append(item)
            by_page[page] = item
            continue
        previous = by_page[page]
        if previous.get("status") == "delivered" and item.get("status") == "delivered" and previous.get("messageId") != item.get("messageId"):
            raise ValueError("Conflicting Telegram message IDs for " + page)
        if rank.get(item.get("status"), 0) > rank.get(previous.get("status"), 0):
            previous.update(item)
        elif item.get("status") == previous.get("status"):
            if item.get("claimId") and previous.get("claimId") not in (None, item["claimId"]):
                raise ValueError("Conflicting Telegram claims for " + page)
            previous.update(item)
    refresh_due(current)
    save(QUEUE, current)
    print("Merged Telegram queue state without downgrading deliveries")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: hourly_telegram.py enqueue <event.json>|prime|claim|send|wake|merge <snapshot.json>")
    modes = {"enqueue": lambda: enqueue(sys.argv[2]), "prime": lambda: claim(prime=True),
             "claim": claim, "send": send, "wake": next_wakeup,
             "merge": lambda: merge(sys.argv[2])}
    if sys.argv[1] not in modes:
        raise SystemExit("Unsupported Telegram queue mode")
    modes[sys.argv[1]]()
