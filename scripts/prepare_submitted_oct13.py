#!/usr/bin/env python3
"""One-time recovery of the owner-approved, already submitted 13 October batch.

Reuses the exact historical review timestamps and employer URLs. Never invents
a Live decision. Does not publish by itself; normal publisher independently
verifies each exact official vacancy and ensures unique website/Telegram jobs.
"""
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit
from admin_publish import validate, normalize_url

ROOT=Path(__file__).resolve().parents[1]
BATCH=ROOT/"data/daily-review-batch.json"
MANIFEST=ROOT/"data/owner-reviewed-publish-retry-20261013.json"
JOBS=ROOT/"data/jobs.json"
IDS=[
 "ahead-3fd5cb37","capgemini-519185","deloitte-112526",
 "ey-1747790","hcltech-161936","mongodb-7922676",
 "startree-6147925004","superapp-8859685002",
 "trackmind-ad66c0ec","veeva-90e4e761",
]
def prepare(path):
    batch=json.loads(BATCH.read_text())
    approval=json.loads(MANIFEST.read_text())
    existing=json.loads(JOBS.read_text())
    expected="2026-10-13-0900-ist"
    if batch.get("batchId")!=expected or batch.get("status")!="submitted":
        raise ValueError("Current batch is not the exact approved October 13 submitted batch")
    publication=batch.get("publication") or {}
    if approval.get("batchId")!=expected or approval.get("requestId")!=publication.get("requestId") or approval.get("candidateIds")!=IDS or publication.get("candidateIds")!=IDS or publication.get("count")!=10:
        raise ValueError("The exact set or identity of ten approved jobs has changed")
    if approval.get("action")!="retry_exact_previously_submitted_jobs" or approval.get("ownerApproved") is not True:
        raise ValueError("Explicit owner approval missing")
    all_candidates={str(c["id"]):c for c in batch.get("priority",[])+batch.get("backup",[])}
    existing_urls={normalize_url(x.get("apply","")) for x in existing}
    existing_pairs={(str(x.get("company","")).casefold(),str(x.get("role","")).casefold()) for x in existing}
    incoming=[]
    for i,id in enumerate(IDS,1):
        c=all_candidates.get(id)
        if not c or c.get("reviewedStatus")!="live" or not c.get("reviewedAt"):
            raise ValueError(f"{id} is missing recorded owner Live approval")
        job=dict(c.get("job") or {})
        original_url=c.get("apply","")
        if job.get("company")!=c.get("company") or job.get("role")!=c.get("role") or job.get("apply")!=original_url or job.get("manualLiveVerifiedAt")!=c.get("reviewedAt") or job.get("status")!="active":
            raise ValueError(f"{id} no longer matches its exact reviewed source or timestamp")
        if urlsplit(original_url).scheme!="https" or not urlsplit(original_url).hostname:
            raise ValueError(f"{id} requires an official HTTPS apply URL")
        if normalize_url(original_url) in existing_urls or (job["company"].casefold(),job["role"].casefold()) in existing_pairs:
            raise ValueError(f"{id} is already published — stop to prevent duplicate Telegram delivery")
        job.setdefault("page","")
        job["manualLiveVerifiedUrl"]=original_url
        validate(job,i)
        incoming.append(job)
    if len(incoming)!=10 or len({normalize_url(x["apply"]) for x in incoming})!=10 or len({x["company"].casefold() for x in incoming})!=10:
        raise ValueError("Duplicate or incomplete ten-job recovery")
    payload={"event_type":"admin_publish_jobs","client_payload":{
        "jobs":incoming,"reviewBatchId":expected,"reviewCandidateIds":IDS,
        "requestId":approval["requestId"],"recoveryFrom":"owner-submitted-20261013"}}
    Path(path).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Recovery prepared exactly 10 recorded owner-approved Live jobs; no new review decision created.")

if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("Usage: prepare_submitted_oct13.py <event-output>")
    try:prepare(sys.argv[1])
    except (ValueError,KeyError,TypeError) as e:raise SystemExit("Recovered publication safely blocked: "+str(e))
