#!/usr/bin/env python3
"""Merge verified Telegram delivery receipts into the latest GitHub main ledger.

Never discard an existing delivered message, overwrite a contradictory
message ID, or send/re-send a Telegram post. This is metadata recovery only.
"""
import json
import sys
from pathlib import Path


def load(path: Path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Receipt file {path} must contain an object")
    return raw


def merge(current, incoming):
    result = dict(current)
    additions = 0
    for key, new in incoming.items():
        if not isinstance(key, str) or "|" not in key or not isinstance(new, dict):
            raise ValueError("Invalid delivery receipt record")
        page = key.split("|", 1)[-1]
        if new.get("page") != page or new.get("status") not in {"delivered", "uncertain"}:
            raise ValueError("Receipt page or status mismatch")
        old = result.get(key)
        if old is not None:
            if not isinstance(old, dict):
                raise ValueError(f"Existing ledger record is invalid for {page}")
            if old.get("status") == "delivered":
                if new.get("status") == "delivered" and str(old.get("messageId")) != str(new.get("messageId")):
                    raise ValueError(f"Different Telegram message IDs recorded for already delivered {page}")
                continue
            if old.get("status") == "uncertain" and new.get("status") == "uncertain":
                continue
        result[key] = new
        additions += 1
    return result, additions


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: merge_telegram_delivery_receipts.py <captured.json> <current.json>")
    captured = load(Path(sys.argv[1]))
    destination = Path(sys.argv[2])
    existing = load(destination) if destination.is_file() else {}
    combined, additions = merge(existing, captured)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(combined, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Safe Telegram receipt merge complete: {additions} new receipts, {len(combined)} total, no Telegram API calls")


if __name__ == "__main__":
    main()
