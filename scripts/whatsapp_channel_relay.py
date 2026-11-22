#!/usr/bin/env python3
"""Opt-in WhatsApp Channel bridge. Unofficial Whapi.Cloud, NOT Meta Cloud API."""
import json,os,re,sys
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/"data/whatsapp-channel-deliveries.json"
TG=ROOT/"data/telegram-deliveries.json"
JOBS=ROOT/"data/jobs.json"
CHANNEL_RE=re.compile(r"^\d{10,18}@newsletter$")

def utc():return datetime.now(timezone.utc).isoformat()
def load(path,default):return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
def save(path,obj):path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def parse(raw):
 try:
  d=datetime.fromisoformat(str(raw).replace("Z","+00:00"))
  return d.astimezone(timezone.utc) if d.tzinfo else None
 except (ValueError,TypeError):return None
def channel():
 c=os.getenv("WHATSAPP_CHANNEL_ID","").strip()
 if not CHANNEL_RE.fullmatch(c):raise RuntimeError("Configure exact @newsletter Channel ID in Actions secrets")
 return c
def request(path,method="GET",payload=None):
 token=os.getenv("WHAPI_TOKEN","").strip()
 if not token:raise RuntimeError("Configure WHAPI_TOKEN secret before connecting")
 body=json.dumps(payload).encode() if payload is not None else None
 req=Request("https://gate.whapi.cloud"+path,data=body,method=method,
   headers={"Authorization":"Bearer "+token,"Accept":"application/json","Content-Type":"application/json"})
 try:
  with urlopen(req,timeout=25) as res:
   if res.status not in (200,201):raise RuntimeError("Whapi HTTP "+str(res.status))
   return json.load(res)
 except HTTPError as ex:raise RuntimeError("Whapi HTTP "+str(ex.code)) from None
def is_admin(data,cid):
 if isinstance(data,list):items=data
 elif isinstance(data,dict):
  items=next((data[k] for k in ("newsletters","data","channels","items") if isinstance(data.get(k),list)),[])
 else:items=[]
 for item in items:
  if not isinstance(item,dict):continue
  if str(item.get("id") or item.get("newsletter_id") or "")!=cid:continue
  return str(item.get("user_role") or item.get("role") or "").lower() in ("admin","owner","creator")
 return False
def check_admin():
 cid=channel()
 if not is_admin(request("/newsletters?count=100"),cid):
  raise RuntimeError("Connected number is not confirmed as an ADMIN of this WhatsApp Channel")
 print("Connected number verified as Channel admin")
def text_for(job):
 page=str(job["page"])
 if not re.fullmatch(r"jobs/[a-z0-9-]+\.html",page):raise RuntimeError("Unsafe job page")
 safe=lambda s,n:re.sub(r"\s+"," ",str(s or "").strip())[:n]
 salary=str(job.get("salary") or "").strip()
 pay=("\n💰 Pay: "+safe(salary,65)) if salary.lower() not in ("","not disclosed","not specified","n/a") else ""
 cat="IT" if job.get("field")=="it" else "Non-IT" if job.get("field")=="nonit" else "Fresher"
 return (f"🚨 *{safe(job.get('company'),80).upper()} HIRING*\n\n"
   f"💼 Role: {safe(job.get('role'),130)}\n📍 Location: {safe(job.get('loc'),85)}\n"
   f"🎓 Experience: {safe(job.get('expYears'),55)}\n💻 Category: {cat}"
   +pay+f"\n\n🔗 Job details & official apply link:\nhttps://hdcareers.in/{page}\n\n"
   "⚠️ Confirm current eligibility and closing status with the employer.\n"
   "Follow HD Careers for more verified fresher jobs.")
def select(doc,tg,jobs,at,run):
 if not doc.get("activationAt"):
  doc["activationAt"]=at
  return None
 activated=parse(doc["activationAt"])
 if not activated:raise RuntimeError("Invalid WhatsApp activation time")
 entries=doc.setdefault("items",{})
 records=[]
 for row in tg.values():
  if not isinstance(row,dict) or row.get("status")!="delivered" or row.get("channel")!="@HD_Careers":continue
  if not row.get("messageId") or not isinstance(row.get("page"),str):continue
  dt=parse(row.get("deliveredAt"))
  if dt and dt>activated:records.append((dt,row))
 for _,r in sorted(records,key=lambda v:v[0]):
  page=r["page"]
  if page in entries:continue
  job=jobs.get(page)
  if not job or job.get("status")!="active":
   entries[page]={"status":"skipped_inactive","at":at}
   continue
  entries[page]={"status":"sending","claimId":run,"at":at,"telegramMessageId":r["messageId"]}
  return page
 return None
def claim():
 if os.getenv("WHATSAPP_CHANNEL_ENABLED")!="true":
  print("WhatsApp bridge disabled. No post.")
  return
 channel()
 run=os.getenv("GITHUB_RUN_ID")
 if not run:raise RuntimeError("Missing unique GitHub job ID")
 doc=load(LEDGER,{"version":1,"activationAt":None,"items":{}})
 tg=load(TG,{})
 jobs={j.get("page"):j for j in load(JOBS,[]) if isinstance(j,dict)}
 page=select(doc,tg,jobs,utc(),run)
 save(LEDGER,doc)
 if os.getenv("GITHUB_OUTPUT"):
  with open(os.environ["GITHUB_OUTPUT"],"a") as f:f.write("claimed="+("true" if page else "false")+"\n")
 print("WhatsApp claimed:",page or "none (initial activation or no new eligible receipt)")
def send():
 if os.getenv("WHATSAPP_CHANNEL_ENABLED")!="true":raise RuntimeError("WhatsApp bridge disabled")
 doc=load(LEDGER,{})
 matches=[(p,v) for p,v in doc.get("items",{}).items()
          if v.get("status")=="sending" and v.get("claimId")==os.getenv("GITHUB_RUN_ID")]
 if len(matches)!=1:raise RuntimeError("No durable sending claim for this run")
 page,entry=matches[0]
 try:
  jobs={j.get("page"):j for j in load(JOBS,[]) if isinstance(j,dict)}
  job=jobs.get(page)
  if not job or job.get("status")!="active":
   entry.update(status="skipped_inactive",checkedAt=utc());return
  from check_job_availability import check
  if check(job).get("state")!="active":
   entry.update(status="skipped_unverified",checkedAt=utc());return
  from publish_verified_telegram import live_job
  if not live_job(job):
   entry.update(status="skipped_site_unavailable",checkedAt=utc());return
  check_admin()
  response=request("/messages/text","POST",{"to":channel(),"body":text_for(job)})
  msg=response.get("message",{}) if isinstance(response,dict) else {}
  mid=(msg.get("id") if isinstance(msg,dict) else None) or response.get("id")
  if not mid:raise RuntimeError("Provider returned no confirmed message ID")
  entry.update(status="provider_accepted",providerMessageId=str(mid),acceptedAt=utc())
  print("Whapi accepted post",page,"provider ID",str(mid)[:60])
 except Exception as exc:
  if entry.get("status")=="sending":
   entry.update(status="uncertain",failedAt=utc(),errorType=type(exc).__name__)
  print("WhatsApp outcome requires manual reconciliation:",page,type(exc).__name__,file=sys.stderr)
  raise
 finally:save(LEDGER,doc)
def main():
 if len(sys.argv)!=2 or sys.argv[1] not in ("claim","send","verify"):
  raise SystemExit("Usage: whatsapp_channel_relay.py claim|send|verify")
 {"claim":claim,"send":send,"verify":check_admin}[sys.argv[1]]()
if __name__=="__main__":main()
