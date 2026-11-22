#!/usr/bin/env python3
"""One-job, owner-requested WhatsApp Channel test for an existing Telegram delivery.

This script does NOT enable normal Whapi automation and does NOT backfill old jobs.
It precommits a durable claim before using the regular live-source-checked sender.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import whatsapp_channel_relay as shared
import whapi_channel_relay as whapi

REQUEST=shared.ROOT/"data"/"whapi-test-request.json"
EXPECTED_CHANNEL="120363419928883930@newsletter"
ALLOWLIST={
    "jobs/qualcomm-cpu-software-engineer.html",
    "jobs/chaosology-technologies-junior-software-developer.html",
    "jobs/brillio-associate-engineer-applications-platforms.html",
}
MAX_TEST_COUNT=3

def claim():
    if os.getenv("WAHA_CHANNEL_ENABLED","").lower()=="true":
        raise RuntimeError("Legacy WAHA automation is enabled: test blocked")
    if os.getenv("WHAPI_CHANNEL_ENABLED","").lower()=="true":
        raise RuntimeError("Production Whapi automation is enabled: test blocked")
    if whapi.channel_id()!=EXPECTED_CHANNEL:
        raise RuntimeError("Whapi target is not the owner-approved HD Career Updates Channel")
    run=os.getenv("GITHUB_RUN_ID","").strip()
    if not run:
        raise RuntimeError("GITHUB_RUN_ID required")
    req=json.loads(REQUEST.read_text(encoding="utf-8"))
    page=req.get("job_page")
    if req.get("test_only") is not True or page not in ALLOWLIST:
        raise RuntimeError("Test request must be exactly one preapproved Telegram job")
    if not req.get("request_id","").startswith("hd-whapi-single-test-20261122-"):
        raise RuntimeError("Unrecognized test request ID")
    ledger=shared.load(shared.LEDGER,{"version":1,"activationAt":None,"items":{}})
    if ledger.get("version")!=1 or not isinstance(ledger.get("items"),dict):
        raise RuntimeError("Unexpected WhatsApp delivery ledger")
    if ledger.get("activationAt") is not None:
        raise RuntimeError("Production relay already activated: stop test")
    items=ledger["items"]
    if page in items:
        raise RuntimeError("Already claimed on WhatsApp; never repost: "+page)
    if sum(1 for x in items.values() if isinstance(x,dict) and x.get("testOnly"))>=MAX_TEST_COUNT:
        raise RuntimeError("Three one-time tests already recorded")
    tg=shared.load(shared.TG,{})
    receipt=tg.get("@HD_Careers|"+page)
    if not isinstance(receipt,dict) or receipt.get("status")!="delivered" or not receipt.get("messageId") or receipt.get("channel")!="@HD_Careers":
        raise RuntimeError("No confirmed Telegram delivery receipt for requested job")
    jobs=shared.load(shared.JOBS,[])
    job=next((j for j in jobs if isinstance(j,dict) and j.get("page")==page),None)
    if not job or job.get("status")!="active":
        raise RuntimeError("Requested job is no longer active in data/jobs.json")
    items[page]={
        "status":"sending","claimId":run,"at":shared.utc(),"testOnly":True,
        "requestId":req["request_id"],"telegramMessageId":receipt["messageId"],
        "telegramDeliveredAt":receipt.get("deliveredAt"),"channelId":EXPECTED_CHANNEL
    }
    shared.save(shared.LEDGER,ledger)
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"],"a",encoding="utf-8") as f:
            f.write("claimed=true\n")
    print("Created one-time pre-send claim for already-Telegram-delivered job:",page)

def main():
    if sys.argv[1:]!=["claim"]:
        raise SystemExit("Usage: whapi_channel_test.py claim")
    claim()

if __name__=="__main__":
    main()
