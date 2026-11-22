#!/usr/bin/env python3
"""Owner-requested one-time edit of the two 22 Nov 2026 Whapi test Channel posts.

Not a send or repost. Fail closed if the original message ID, exact old footer,
linked job URL, Channel admin rights or API edit semantics cannot be confirmed.
A precommitted claim prevents accidentally editing twice.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import whatsapp_channel_relay as shared
import whapi_channel_relay as whapi

REQUEST = shared.ROOT / "data" / "whapi-old-footer-edit-request.json"
AUDIT = shared.ROOT / "data" / "whapi-old-footer-edits.json"
CHANNEL = "120363419928883930@newsletter"
PAGES = (
    "jobs/chaosology-technologies-junior-software-developer.html",
    "jobs/brillio-associate-engineer-applications-platforms.html",
)
OLD = ("⚠️ Application status can change. Confirm current eligibility with the employer.\n"
       "Follow HD Careers for more verified fresher jobs.")
NEW = ("💚 *WhatsApp:* https://whatsapp.com/channel/0029VbAxOna7NoZvhuKX362z\n"
       "✈️ *Telegram:* https://t.me/HD_Careers")

def lists_from(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("messages", "items", "data"):
            if key in value:
                return lists_from(value[key])
    return []

def flatten_strings(x):
    if isinstance(x, str):
        return [x]
    if isinstance(x, list):
        return [s for y in x for s in flatten_strings(y)]
    if isinstance(x, dict):
        return [s for y in x.values() for s in flatten_strings(y)]
    return []

def find_text(row):
    candidates = [
        row.get("body"), row.get("text"), row.get("content"), row.get("message"),
        row.get("link_preview")
    ]
    for value in candidates:
        if isinstance(value, str) and "hdcareers.in/jobs/" in value:
            return value
        if isinstance(value, dict):
            for k in ("body", "text", "content"):
                s = value.get(k)
                if isinstance(s, str) and "hdcareers.in/jobs/" in s:
                    return s
    return None

def assert_config():
    if whapi.channel_id() != CHANNEL:
        raise RuntimeError("Unexpected WhatsApp Channel: editing blocked")

def claim():
    assert_config()
    run = os.getenv("GITHUB_RUN_ID", "")
    if not run:
        raise RuntimeError("GitHub run ID required")
    request = json.loads(REQUEST.read_text())
    if request != {"requestId": "hdcareers-footer-edit-20261122",
                   "targetChannel": "HD Career Updates", "editOnly": True,
                   "pages": list(PAGES)}:
        raise RuntimeError("Not an exact owner-approved legacy footer edit request")
    if AUDIT.exists():
        raise RuntimeError("Legacy edit was already claimed: do not repeat")
    past = shared.load(shared.LEDGER, {})
    entries = {}
    for page in PAGES:
        rec = past.get("items", {}).get(page, {})
        if (rec.get("status") != "provider_accepted" or
            rec.get("testOnly") is not True or
            rec.get("channelId") != CHANNEL or
            not rec.get("providerMessageId")):
            raise RuntimeError("No exact previously published test receipt: " + page)
        entries[page] = {"status": "claimed_before_edit", "originalMessageId": rec["providerMessageId"]}
    shared.save(AUDIT, {"version": 1, "claimId": run, "claimedAt": shared.utc(), "items": entries})
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write("claimed=true\n")
    print("Safely claimed two existing messages for EDIT only (no new posts)")

def edit():
    assert_config()
    doc = shared.load(AUDIT, {})
    run = os.getenv("GITHUB_RUN_ID", "")
    if doc.get("claimId") != run:
        resume = os.getenv("WHAPI_EDIT_RESUME_CLAIM_ID", "")
        if resume != "45014694619" or doc.get("claimId") != resume:
            raise RuntimeError("Precommitted edit claim does not belong to this run")
        if any(entry.get("status") != "claimed_before_edit" for entry in doc.get("items", {}).values()):
            raise RuntimeError("Resume blocked: previous edit attempt state changed")
        print("Resuming only preclaimed edits after read-only field-shape inspection; no post was attempted previously")
    whapi.verify_admin()
    response = whapi.api("/newsletters/" + CHANNEL + "/messages?count=50")
    records = lists_from(response)
    print("Found Channel history messages:", len(records))
    errors = []
    for page in PAGES:
        record = doc["items"][page]
        if record.get("status") != "claimed_before_edit":
            raise RuntimeError("Edit was already attempted for " + page)
        original_id = record["originalMessageId"]
        candidates = [row for row in records
                      if isinstance(row, dict) and original_id in flatten_strings(row)]
        if len(candidates) != 1:
            record.update(status="skipped_message_not_found", checkedAt=shared.utc())
            errors.append(page + ": historical ID was not uniquely found")
            continue
        old_text = find_text(candidates[0])
        if not old_text or ("https://hdcareers.in/" + page) not in old_text:
            record.update(status="skipped_body_unavailable", checkedAt=shared.utc())
            errors.append(page + ": original body not verified")
            continue
        if OLD not in old_text:
            record.update(status="already_new_footer" if NEW in old_text else "skipped_not_old_footer",
                          checkedAt=shared.utc())
            continue
        updated_body = old_text.replace(OLD, NEW, 1)
        try:
            # The explicit edit parameter is required; never send an ordinary post.
            result = whapi.api("/messages/text", "POST",
                               {"to": CHANNEL, "edit": original_id, "body": updated_body})
            accepted = whapi.message_id(result)
            if not accepted:
                raise RuntimeError("Provider returned no edit confirmation message ID")
            record.update(status="edit_provider_accepted", editedAt=shared.utc(),
                          responseMessageId=accepted)
            print("Whapi accepted message EDIT only:", page)
        except Exception as error:
            record.update(status="edit_uncertain_no_retry", attemptedAt=shared.utc(),
                          errorType=type(error).__name__)
            errors.append(page + ": provider outcome uncertain, no retry")
        finally:
            shared.save(AUDIT, doc)
    if errors:
        raise RuntimeError("; ".join(errors))
    print("All existing posts edited or already updated. No new posts were sent.")

if __name__ == "__main__":
    if sys.argv[1:] == ["claim"]:
        claim()
    elif sys.argv[1:] == ["edit"]:
        edit()
    else:
        raise SystemExit("Usage: edit_whapi_legacy_footer.py claim|edit")
