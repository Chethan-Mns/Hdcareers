#!/usr/bin/env python3
"""Read-only official-source comparison of the six ATS QA candidates."""
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from check_job_availability import check, has_high_confidence_live

ROOT=Path(__file__).resolve().parents[1]
BATCH=ROOT/"data/testing/ats-platform-six-20261018.json"

def verify(batch,fn=check):
    results=[]
    for row in batch["jobs"]:
        job={"id":row["id"],"company":row["company"],"role":row["role"],
             "apply":row["url"],"jobId":row["reqId"],
             "status":"review"}
        try:
            observed=fn(job)
        except Exception as exc:
            observed={"state":"review","reason":"Official-source check inconclusive ("+type(exc).__name__+")"}
        results.append({
            "id":row["id"],"provider":row["provider"],"company":row["company"],
            "role":row["role"],"officialUrl":row["url"],
            "observedState":observed.get("state","review"),
            "verifiedLive":has_high_confidence_live(job,observed),
            "evidence":observed.get("reason","Unknown"),
        })
    return {"batchId":batch["batchId"],"scannedAt":datetime.now(timezone.utc).isoformat(),
            "checked":len(results),"verifiedLive":sum(x["verifiedLive"] for x in results),
            "uncertainOrExpired":sum(not x["verifiedLive"] for x in results),
            "jobs":results,"safeMode":True,
            "notice":"Read-only evidence snapshot. No owner decisions, GitHub job data, public pages or Telegram records changed."}

if __name__=="__main__":
    report=verify(json.loads(BATCH.read_text(encoding="utf-8")))
    destination=ROOT/"data/testing/ats-platform-six-checker-results.json"
    if len(sys.argv)>1:destination=Path(sys.argv[1])
    destination.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    for j in report["jobs"]:
        print(j["provider"],j["company"],j["observedState"],j["verifiedLive"],j["evidence"][:130])
    print("Confirmed Live:",report["verifiedLive"],"/",report["checked"])
