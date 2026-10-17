"""At-most-once, one job per hour Telegram queue, using the existing audited sender."""
from __future__ import annotations
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
QUEUE=ROOT/"data"/"telegram-hourly-queue.json"
LEDGER=ROOT/"data"/"telegram-deliveries.json"
MANIFEST=ROOT/"data"/"telegram-approved-batch.json"
JOBS=ROOT/"data"/"jobs.json"

def load(p, fallback):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else fallback

def save(p, obj):
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def iso():
    return datetime.now(timezone.utc).isoformat()

def queue():
    q=load(QUEUE,{"version":1,"intervalMinutes":60,"items":[]})
    if not isinstance(q,dict) or q.get("version")!=1 or q.get("intervalMinutes")!=60 or not isinstance(q.get("items"),list):
        raise ValueError("Invalid hourly Telegram queue")
    return q

def output(name,value):
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"],"a",encoding="utf-8") as f: f.write(f"{name}={value}\n")

def enqueue(eventfile):
    payload=load(Path(eventfile),{})
    if payload.get("client_payload",{}).get("telegramDeliveryMode")!="hourly":
        print("Instant delivery selected; no hourly queue changed")
        return
    manifest=load(MANIFEST,{})
    expected="admin-"+str(os.getenv("GITHUB_RUN_ID",""))
    if manifest.get("batchId")!=expected or manifest.get("approved") is not True:
        print("No newly verified pages for this workflow run")
        return
    pages=manifest.get("pages",[])
    if len(pages)>20 or len(pages)!=len(set(pages)):
        raise ValueError("Invalid approved pages")
    site={j.get("page") for j in load(JOBS,[])}
    q=queue()
    old={x["page"] for x in q["items"]}
    ledger=load(LEDGER,{})
    added=[]
    for page in pages:
        if not isinstance(page,str) or not page.startswith("jobs/") or not page.endswith(".html") or page not in site:
            raise ValueError("Approved page is not present in website job data")
        if page in old or any(v.get("page")==page and v.get("status")=="delivered" for v in ledger.values()):
            print("Skipping already queued/delivered page:",page)
            continue
        q["items"].append({"page":page,"batchId":expected,"status":"pending","queuedAt":iso()})
        added.append(page)
    if added: save(QUEUE,q)
    print(f"Hourly Telegram queued {len(added)} new verified pages: {added}")

def claim():
    q=queue()
    run=str(os.getenv("GITHUB_RUN_ID","")).strip()
    if not run: raise ValueError("GITHUB_RUN_ID is mandatory for at-most-once claim")
    if any(x.get("status")=="sending" for x in q["items"]):
        print("Prior send has unresolved claim; stopping to prevent duplicate messages")
        output("claimed","false");return
    ledger=load(LEDGER,{})
    for item in q["items"]:
        if item.get("status")!="pending": continue
        sent=next((x for x in ledger.values() if x.get("page")==item["page"] and x.get("status")=="delivered"),None)
        if sent:
            item.update({"status":"already-delivered","deliveredAt":sent.get("deliveredAt"),"messageId":sent.get("messageId")})
    last=[datetime.fromisoformat(x["deliveredAt"].replace("Z","+00:00")) for x in q["items"] if x.get("status")=="delivered" and x.get("deliveredAt")]
    if last and datetime.now(timezone.utc)-max(last)<timedelta(minutes=q["intervalMinutes"]):
        print("60-minute spacing not yet reached")
        save(QUEUE,q); output("claimed","false");return
    next_item=next((x for x in q["items"] if x.get("status")=="pending"),None)
    if not next_item:
        save(QUEUE,q);print("No pending pages");output("claimed","false");return
    next_item.update({"status":"sending","claimId":run,"claimedAt":iso()})
    save(QUEUE,q)
    output("claimed","true")
    output("page",next_item["page"])
    print("Claimed for one-time send:",next_item["page"])

def send():
    run=str(os.getenv("GITHUB_RUN_ID","")).strip()
    q=queue()
    item=next((x for x in q["items"] if x.get("status")=="sending" and x.get("claimId")==run),None)
    if not item:
        raise ValueError("No persisted sending claim belongs to this run")
    page=item["page"]
    os.environ["JOB_PAGES"]=page
    try:
        from publish_approved_telegram import publish
        publish()
        ledger=load(LEDGER,{})
        receipt=next((v for v in ledger.values() if v.get("page")==page and v.get("status")=="delivered"),None)
        if not receipt: raise RuntimeError("Message ID missing after Telegram send")
        item.update({"status":"delivered","messageId":receipt.get("messageId"),"deliveredAt":receipt.get("deliveredAt") or iso()})
        print("Hourly delivery confirmed:",page,item["messageId"])
    except Exception as exc:
        # Never auto-retry after a send attempt: response/receipt may be ambiguous.
        item.update({"status":"uncertain","lastError":str(exc)[:360],"failedAt":iso()})
        save(QUEUE,q)
        print("Delivery held for human inspection (no automatic retry):",page,str(exc),file=sys.stderr)
        raise
    save(QUEUE,q)

if __name__=="__main__":
    if len(sys.argv)<2: raise SystemExit("Usage: hourly_telegram.py enqueue <event.json>|claim|send")
    {"enqueue":lambda:enqueue(sys.argv[2]),"claim":claim,"send":send}[sys.argv[1]]()
