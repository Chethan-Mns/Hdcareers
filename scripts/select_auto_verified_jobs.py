#!/usr/bin/env python3
"""Select high-confidence Fresher IT/Non-IT and internship jobs; no human decision fabricated."""
import argparse,hashlib,json,re
from datetime import datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urlsplit,parse_qsl,urlencode,urlunsplit
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
IST=ZoneInfo("Asia/Kolkata")
ATS=("greenhouse.io","lever.co","ashbyhq.com","smartrecruiters.com")
CONFIRMED=("public posting inventory contains the exact published job",
 "exact role and application call-to-action found on official url",
 "verification terms and registration/submit control found on official url")
BAD_HOSTS=("naukri.com","indeed.com","linkedin.com","glassdoor.com","shine.com","internshala.com","talentbridge.cisco.com")
REQUIRED=("company","role","loc","elig","desc","apply","sourceName")
TYPES=("fresher","internship/apprenticeship")
CATS=("it","nonit","internship","apprenticeship","campus","remote","walkin")
def load(path,default):return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
def parse(raw):
 try:
  dt=datetime.fromisoformat(str(raw).replace("Z","+00:00"))
  return dt if dt.tzinfo else None
 except (ValueError,TypeError):return None
def key(u):
 p=urlsplit(str(u or ""))
 query=sorted((k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if not k.lower().startswith("utm_") and k.lower() not in ("source","fbclid","gclid","ref"))
 return urlunsplit((p.scheme.lower(),p.netloc.lower().removeprefix("www."),p.path.rstrip("/"),urlencode(query),""))
def employer(s):return re.sub("[^a-z0-9]+"," ",str(s or "").lower()).strip()
def evidence(row,now):
 t=parse(row.get("precheckCheckedAt"))
 r=str(row.get("precheckReason") or "").lower()
 return row.get("precheckStatus")=="source-active" and bool(t) and timedelta(0)<=now-t<=timedelta(hours=18) and any(k in r for k in CONFIRMED)
def eligible(row):
 j=row.get("job")
 if not isinstance(j,dict) or any(len(str(j.get(k) or "").strip())<3 for k in REQUIRED):return False
 if len(str(j["desc"]).strip())<100 or len(str(j["elig"]).strip())<25:return False
 if not isinstance(j.get("resp"),list) or not any(str(v).strip() for v in j["resp"]):return False
 if not isinstance(j.get("skills"),list) or not j["skills"]:return False
 if row.get("reviewedStatus") in ("expired","unsure"):return False
 if row.get("reviewedStatus")=="live" and not row.get("reviewedAt"):return False
 if j.get("status") not in ("unreviewed","active"):return False
 if row.get("apply")!=j.get("apply"):return False
 if j.get("expType") not in TYPES:return False
 cat=str(j.get("cat") or "").lower()
 if cat in ("non-it","non it"):cat="nonit"
 if cat not in CATS:return False
 if j.get("expType")=="internship/apprenticeship" and cat not in ("internship","apprenticeship"):return False
 if re.search(r"\b(senior|lead engineer|principal|manager|director|architect|head of)\b",str(j.get("role") or ""),re.I):return False
 if re.search(r"\b(?:minimum|at least)?\s*[4-9]\+?\s*(?:years|yrs)\s*(?:of)?\s*experience",str(j.get("expYears") or ""),re.I):return False
 try:
  p=urlsplit(j["apply"]);h=(p.hostname or "").lower()
  if p.scheme!="https" or not h or not p.path.strip("/") or p.username or p.password or p.port not in (None,443):return False
  if any(h==v or h.endswith("."+v) for v in BAD_HOSTS):return False
 except ValueError:return False
 return True
def normalize(row,now):
 j=dict(row["job"]);company=str(j["company"]).strip();role=str(j["role"]).strip()
 cat=str(j["cat"]).lower()
 j["cat"]={"non-it":"nonit","non it":"nonit"}.get(cat,cat)
 j["field"]=j["field"] if j.get("field") in ("it","nonit") else ("nonit" if j["cat"]=="nonit" else "it")
 j["status"]="active";j["expType"]="fresher"
 j["roleTag"]=j.get("roleTag") or role
 j["locationFilter"]=j.get("locationFilter") or j["loc"]
 j["domain"]=j.get("domain") or (urlsplit(j["apply"]).hostname or "")
 j["salary"]=j.get("salary") or "Not Disclosed"
 j["batch"]=j.get("batch") or "Refer to employer eligibility"
 j["expYears"]=j.get("expYears") or "Fresher eligible"
 j["workMode"]=j.get("workMode") or "Not Specified"
 j["date"]=j.get("date") or now.astimezone(IST).strftime("%d %b %Y")
 j["verifiedDate"]=now.astimezone(IST).strftime("%d %b %Y")
 if not isinstance(j.get("logo"),list) or len(j["logo"])!=2:
  initials="".join(s[0] for s in company.split() if s and s[0].isalpha())[:2].upper() or "HC"
  j["logo"]=[initials,"#0b6fe8"]
 j["who"]=j.get("who") or "Applicants meeting the employer's stated eligibility: "+str(j["elig"])[:500]
 slug=re.sub("[^a-z0-9]+","-",(company+" "+role).lower()).strip("-")[:75]
 j["page"]=j.get("page") or "jobs/"+slug+".html"
 for k in ("manualLiveVerifiedAt","manualLiveVerifiedUrl","browserVerifiedAt"):j.pop(k,None)
 j["autoVerified"]=True
 j["autoVerifiedSource"]=str(row["precheckReason"])
 j["autoVerifiedAt"]=str(row["precheckCheckedAt"])
 return j
def select(batch,published,pending,ledger,now=None,limit=10):
 now=now or datetime.now(timezone.utc)
 bid=str(batch.get("batchId") or "")
 if batch.get("status")!="reviewing":return [],"batch is not open"
 if not bid.startswith(now.astimezone(IST).strftime("%Y-%m-%d")+"-"):return [],"batch is not today"
 generated=parse(batch.get("generatedAt"))
 if not generated or not timedelta(0)<=now-generated<=timedelta(hours=24):return [],"batch is stale"
 if any(x.get("batchId")==bid for x in ledger.get("batches",[])):return [],"batch already claimed"
 urls={key(j.get("apply")) for j in published}
 pairs={(employer(j.get("company")),str(j.get("role") or "").casefold()) for j in published}
 for x in pending:
  if x.get("state") in ("ready","review") and isinstance(x.get("job"),dict):
   urls.add(key(x["job"].get("apply")))
 seen=set();companies=set();selected=[]
 for row in list(batch.get("priority") or [])+list(batch.get("backup") or []):
  if not evidence(row,now) or not eligible(row):continue
  j=row["job"];u=key(j["apply"]);e=employer(j["company"]);pair=(e,str(j["role"]).casefold())
  if not u or u in urls or ("url",u) in seen or pair in pairs or ("pair",pair) in seen or e in companies:continue
  job=normalize(row,now);job["autoVerifiedBatchId"]=bid
  selected.append((str(row["id"]),job));seen.update({("url",u),("pair",pair)});companies.add(e)
  if len(selected)>=limit:break
 return selected,("selected" if selected else "no new jobs met verification and content criteria")
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--event",required=True);ap.add_argument("--report",required=True);args=ap.parse_args()
 d=ROOT/"data";batch=load(d/"daily-review-batch.json",{});existing=load(d/"jobs.json",[])
 reviews=load(d/"review-queue.json",[]);ledger=load(d/"auto-publish-ledger.json",{"batches":[]})
 chosen,reason=select(batch,existing,reviews,ledger)
 summary={"batchId":batch.get("batchId"),"selected":len(chosen),"candidateIds":[i for i,_ in chosen],
  "companies":[x["company"] for _,x in chosen],"reason":reason}
 if chosen:
  request=hashlib.sha256((str(batch["batchId"])+"|"+",".join(i for i,_ in chosen)).encode()).hexdigest()[:24]
  summary["requestId"]=request
  event={"event_type":"admin_publish_jobs","client_payload":{
   "jobs":[x for _,x in chosen],"requestId":request,
   "autoVerifiedBatchId":batch["batchId"],"telegramDeliveryMode":"hourly"}}
  Path(args.event).write_text(json.dumps(event,ensure_ascii=False,indent=2)+"\n")
 Path(args.report).write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
 print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__":main()
