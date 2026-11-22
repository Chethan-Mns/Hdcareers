#!/usr/bin/env python3
"""Whapi.Cloud WhatsApp Channel mirror of confirmed HD Careers Telegram deliveries.

Disabled by default. Uses the existing no-backfill, pre-send-claim ledger
and live-employer verification from whatsapp_channel_relay.py.
Whapi.Cloud is an UNOFFICIAL WhatsApp web-session gateway.
"""
from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

import whatsapp_channel_relay as shared

API_BASE = "https://gate.whapi.cloud"


def channel_id():
    cid = os.getenv("WHAPI_CHANNEL_ID", "").strip()
    if not shared.CHANNEL_RE.fullmatch(cid):
        raise ValueError("WHAPI_CHANNEL_ID must be the exact @newsletter ID, not an invite link")
    return cid


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def api(path, method="GET", payload=None):
    if not path.startswith("/") or path.startswith("//"):
        raise ValueError("Invalid Whapi endpoint")
    token = os.getenv("WHAPI_TOKEN", "").strip()
    if len(token) < 16:
        raise RuntimeError("WHAPI_TOKEN is not configured")
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = Request(API_BASE + path, data=data, method=method, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "HDCareers-Whapi-Mirror/1.0",
    })
    try:
        with build_opener(NoRedirect()).open(req, timeout=22) as res:
            if res.status not in (200, 201, 202):
                raise RuntimeError("Whapi HTTP " + str(res.status))
            result = json.loads(res.read(180000))
            if not isinstance(result, dict):
                raise RuntimeError("Unexpected Whapi response")
            return result
    except HTTPError as err:
        raise RuntimeError("Whapi HTTP " + str(err.code)) from None
    except (URLError, TimeoutError):
        raise RuntimeError("Whapi unreachable") from None
    except json.JSONDecodeError:
        raise RuntimeError("Whapi returned invalid JSON") from None


def admin_status(result, cid):
    doc = result.get("newsletter", result)
    if not isinstance(doc, dict):
        return False
    role = doc.get("user_role") or doc.get("role")
    return doc.get("id") == cid and str(role or "").lower() in ("admin", "owner")


def verify_admin():
    cid = channel_id()
    result = api("/newsletters/" + quote(cid, safe="@"))
    if not admin_status(result, cid):
        raise RuntimeError("Connected Whapi number is not OWNER/ADMIN of configured Channel")
    print("Whapi Channel admin check passed; channel ID verified")


def must_be_enabled():
    if os.getenv("WHAPI_CHANNEL_ENABLED", "").lower() != "true":
        raise RuntimeError("Whapi Channel relay disabled")
    if os.getenv("WAHA_CHANNEL_ENABLED", "").lower() == "true":
        raise RuntimeError("Disable old WAHA relay before enabling Whapi")


def claim():
    must_be_enabled()
    channel_id()
    run = os.getenv("GITHUB_RUN_ID", "").strip()
    if not run:
        raise RuntimeError("GITHUB_RUN_ID required")
    doc = shared.load(shared.LEDGER, {"version": 1, "activationAt": None, "items": {}})
    if doc.get("version") != 1 or not isinstance(doc.get("items"), dict):
        raise RuntimeError("Unexpected WhatsApp delivery ledger format")
    jobs = {
        str(job.get("page")): job
        for job in shared.load(shared.JOBS, []) if isinstance(job, dict)
    }
    page = shared.select(doc, shared.load(shared.TG, {}), jobs, shared.utc(), run)
    shared.save(shared.LEDGER, doc)
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write("claimed=" + ("true" if page else "false") + "\n")
    print("Whapi selected:", page or "none (activated or no new Telegram receipt)")


def message_id(result):
    if result.get("sent") is False:
        return None
    msg = result.get("message", result)
    if not isinstance(msg, dict):
        return None
    value = msg.get("id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict):
        sub = value.get("_serialized") or value.get("id")
        if isinstance(sub, str) and sub.strip():
            return sub.strip()
    return None


def send():
    must_be_enabled()
    doc = shared.load(shared.LEDGER, {})
    run = os.getenv("GITHUB_RUN_ID", "").strip()
    matches = [
        (page, item) for page, item in doc.get("items", {}).items()
        if isinstance(item, dict) and item.get("status") == "sending"
        and item.get("claimId") == run
    ]
    if len(matches) != 1:
        raise RuntimeError("No unique precommitted Whapi claim")
    page, item = matches[0]
    try:
        jobs = {
            job.get("page"): job
            for job in shared.load(shared.JOBS, []) if isinstance(job, dict)
        }
        job = jobs.get(page)
        if not job or job.get("status") != "active":
            item.update(status="skipped_inactive", checkedAt=shared.utc())
            return
        from check_job_availability import check
        verdict = check(job)
        if verdict.get("state") != "active":
            item.update(status="skipped_unverified",
                        checkState=verdict.get("state", "review"), checkedAt=shared.utc())
            return
        from publish_verified_telegram import live_job
        if not live_job(job):
            item.update(status="skipped_site_unavailable", checkedAt=shared.utc())
            return
        verify_admin()
        result = api("/messages/text", "POST", {
            "to": channel_id(),
            "body": shared.fmt(job),
        })
        mid = message_id(result)
        if not mid:
            raise RuntimeError("Whapi returned no confirmed message ID")
        item.update(status="provider_accepted", providerMessageId=mid,
                    acceptedAt=shared.utc(), provider="Whapi.Cloud",
                    channelId=channel_id())
        print("Whapi accepted Channel post:", page, "message-id:", mid[:70])
    except Exception as err:
        if item.get("status") == "sending":
            item.update(status="uncertain", failedAt=shared.utc(),
                        errorType=type(err).__name__)
        print("Whapi outcome needs manual reconciliation:", page,
              type(err).__name__, file=sys.stderr)
        raise
    finally:
        shared.save(shared.LEDGER, doc)


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("verify", "claim", "send"):
        raise SystemExit("Usage: whapi_channel_relay.py verify|claim|send")
    {"verify": verify_admin, "claim": claim, "send": send}[sys.argv[1]]()
