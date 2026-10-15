"""Two separate read-only live employer scans, with no production writes.

Two samples spaced one minute apart are smoke tests, NOT two daily schedules.
Job owner observations are historical and never silently overwritten.
"""
import copy
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
from check_job_availability import check

CASES=(75,82,104,145,146,147,109,108)
OUTPUT=Path("phase2-two-live-source-cycles.json")

def inspect(job):
    target=copy.deepcopy(job)
    # Do not allow old confirmations to influence independent evidence.
    for k in ("manualLiveVerifiedAt","manualLiveVerifiedUrl","browserVerifiedAt"):
        target.pop(k,None)
    try:
        result=check(target)
        state=result.get("state","review")
        if state not in ("active","expired","review"):
            state="review"
        return {"id":job["id"],"company":job["company"],"storedStatus":job["status"],
            "ownerClosed":bool(job.get("manualClosedVerifiedAt")),
            "state":state,"reason":result.get("reason",""),
            "checkedAt":result.get("checkedAt",datetime.now(timezone.utc).isoformat()),
            "reopeningEligible":state=="active" and job["status"]=="expired"
                and not job.get("manualClosedVerifiedAt")
                and result.get("reason","").startswith("Reopening confirmed:")}
    except Exception as exc:
        return {"id":job["id"],"company":job["company"],"storedStatus":job["status"],
            "ownerClosed":bool(job.get("manualClosedVerifiedAt")),
            "state":"review","reason":"Probe failed: "+type(exc).__name__,
            "checkedAt":datetime.now(timezone.utc).isoformat(),"reopeningEligible":False}

def main():
    jobs={int(j["id"]):j for j in json.loads((ROOT/"data/jobs.json").read_text())}
    expected={75:"Deloitte USI",82:"NielsenIQ",104:"ServiceNow",
        145:"StarTree",146:"SuperApp",147:"Trackmind",109:"Rubrik",108:"Visa"}
    assert all(jobs[x]["company"]==c for x,c in expected.items())
    report={"mode":"two_cycle_real_source_read_only","productionWrites":False,
        "telegramMessagesSent":0,"mainStatusChanges":0,"minIntervalSeconds":60,
        "startedAt":datetime.now(timezone.utc).isoformat(),"rounds":[]}
    try:
        for round_no in (1,2):
            if round_no==2:
                elapsed=time.monotonic()-report_start
                time.sleep(max(0,60-elapsed))
            now=datetime.now(timezone.utc).isoformat()
            with ThreadPoolExecutor(max_workers=6) as pool:
                tasks=[pool.submit(inspect,jobs[x]) for x in CASES]
                results=[f.result() for f in tasks]
            results.sort(key=lambda r:CASES.index(r["id"]))
            report["rounds"].append({"round":round_no,"startedAt":now,
                "results":results,"reopeningCandidates":[x["id"] for x in results if x["reopeningEligible"]],
                "definitiveExpiryOfActive":[x["id"] for x in results if x["storedStatus"]=="active" and x["state"]=="expired"]})
            if round_no==1:
                report_start=time.monotonic()
            print("ROUND",round_no,"RESULTS",[(x["id"],x["state"],x["reason"][:100]) for x in results],flush=True)
            OUTPUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    finally:
        report["finishedAt"]=datetime.now(timezone.utc).isoformat()
        OUTPUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    assert len(report["rounds"])==2
    assert [r["id"] for r in report["rounds"][0]["results"]]==list(CASES)
    assert [r["id"] for r in report["rounds"][1]["results"]]==list(CASES)
    print("LIVE_SOURCE_SHADOW_FINISHED; no status changes and no Telegram sends",flush=True)

if __name__=="__main__":
    main()
