#!/usr/bin/env python3
"""Official-source precheck for unreviewed daily candidates; never auto-expire."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime,timezone
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from check_job_availability import check

def label(result):
    return "source-closed" if result.get("state")=="expired" else "source-active" if result.get("state")=="active" else "unsure"

def run(path,apply=False):
    file=Path(path);batch=json.loads(file.read_text(encoding="utf-8"))
    items=list(batch.get("priority") or [])+list(batch.get("backup") or [])
    if batch.get("status")!="reviewing" or any(x.get("reviewedAt") or x.get("reviewedStatus") in ("live","expired","unsure") for x in items):
        print("Owner decisions already exist or batch is finalized: no precheck edits.")
        return
    def probe(item):
        j=dict(item.get("job") or item)
        j["id"]=item.get("id");j["role"]=item.get("role") or j.get("role")
        j["apply"]=item.get("apply") or j.get("apply")
        j["manualLiveVerifiedAt"]=None;j["browserVerifiedAt"]=None
        if not str(j.get("apply","")).startswith("https://") or not j.get("role"):
            return {"state":"review","reason":"Missing exact employer URL or role"}
        return check(j)
    result={}
    with ThreadPoolExecutor(max_workers=5) as pool:
        pending={pool.submit(probe,item):item for item in items}
        for task in as_completed(pending):
            item=pending[task]
            try:response=task.result()
            except Exception as exc:response={"state":"review","reason":"Request unavailable: "+type(exc).__name__}
            result[str(item.get("id"))]=response
    when=datetime.now(timezone.utc).isoformat()
    count={"source-active":0,"source-closed":0,"unsure":0}
    for item in items:
        signal=result[str(item.get("id"))]
        status=label(signal)
        item.update(precheckStatus=status,precheckReason=str(signal.get("reason") or "Source unconfirmed")[:350],precheckCheckedAt=when)
        count[status]+=1
    print("Source precheck (no manual verdict changed):",count)
    if apply:
        file.write_text(json.dumps(batch,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("path",nargs="?",default=str(ROOT/"data/daily-review-batch.json"))
    p.add_argument("--apply",action="store_true")
    args=p.parse_args()
    run(args.path,args.apply)
