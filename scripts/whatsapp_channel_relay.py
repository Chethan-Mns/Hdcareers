#!/usr/bin/env python3
"""HD Careers: free self-hosted WAHA Channel mirror from confirmed Telegram receipts.

This is an unofficial WhatsApp Web integration, not Meta's Cloud API.
Safe default: disabled. No old Telegram posts are backfilled on first activation.
Claim persists BEFORE remote send. Errors never cause blind reposting.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime,timezone
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.parse import quote,urlsplit
from urllib.request import HTTPRedirectHandler,Request,build_opener

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/"data"/"whatsapp-channel-deliveries.json"
TG=ROOT/"data"/"telegram-deliveries.json"
JOBS=ROOT/"data"/"jobs.json"
CHANNEL_RE=re.compile(r"^[0-9]{6,24}@newsletter$")
SESSION_RE=re.compile(r"^[a-zA-Z0-9_-]{1,50}$")
PAGE_RE=re.compile(r"^jobs/[a-z0-9-]+\.html$")


def utc():return datetime.now(timezone.utc).isoformat()


def parse(raw):
    try:
        t=datetime.fromisoformat(str(raw).replace("Z","+00:00"))
        return t.astimezone(timezone.utc) if t.tzinfo else None
    except (ValueError,TypeError,OverflowError):return None


def load(path,default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save(path,doc):
    path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def configured_channel():
    cid=os.getenv("WAHA_CHANNEL_ID","").strip()
    if not CHANNEL_RE.fullmatch(cid):
        raise ValueError("WAHA_CHANNEL_ID must be the exact existing @newsletter ID")
    return cid


def configured_session():
    value=os.getenv("WAHA_SESSION","default").strip()
    if not SESSION_RE.fullmatch(value):raise ValueError("WAHA_SESSION is invalid")
    return value


def configured_endpoint():
    url=os.getenv("WAHA_BASE_URL","").strip().rstrip("/")
    try:
        p=urlsplit(url)
        if (p.scheme!="https" or not p.hostname or p.username or p.password
            or p.path not in ("","/") or p.query or p.fragment or p.port not in (None,443)):
            raise ValueError()
    except ValueError:
        raise RuntimeError("WAHA_BASE_URL must be an HTTPS hostname with valid TLS")
    return url


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None


def api(path,method="GET",payload=None):
    url=configured_endpoint()+path
    key=os.getenv("WAHA_API_KEY","").strip()
    if len(key)<24:raise RuntimeError("WAHA_API_KEY is not configured")
    data=json.dumps(payload,ensure_ascii=False).encode("utf-8") if payload is not None else None
    req=Request(url,data=data,method=method,headers={
        "X-Api-Key":key,"Accept":"application/json",
        "Content-Type":"application/json","User-Agent":"HDCareers-WAHA-Bridge/1.0"})
    try:
        with build_opener(NoRedirect()).open(req,timeout=22) as res:
            if res.status not in (200,201,202):raise RuntimeError("WAHA HTTP "+str(res.status))
            result=json.loads(res.read(180000))
            if not isinstance(result,(dict,list)):raise RuntimeError("Unexpected WAHA response")
            return result
    except HTTPError as error:
        # Redirects are refused to avoid sending the key to another hostname.
        raise RuntimeError("WAHA HTTP "+str(error.code)) from None
    except (URLError,TimeoutError):
        raise RuntimeError("WAHA unreachable; check cloud host and TLS") from None
    except json.JSONDecodeError:
        raise RuntimeError("WAHA returned invalid JSON") from None


def admin_status(channels,cid):
    items=channels if isinstance(channels,list) else (
        channels.get("data",channels.get("channels",[])) if isinstance(channels,dict) else [])
    if isinstance(items,dict):items=items.get("items",[])
    if not isinstance(items,list):return False
    return any(isinstance(row,dict) and row.get("id")==cid
               and str(row.get("role") or "").upper() in ("OWNER","ADMIN") for row in items)


def verify_admin():
    cid=configured_channel()
    session=configured_session()
    result=api("/api/"+quote(session,safe="")+"/channels")
    if not admin_status(result,cid):
        raise RuntimeError("Connected WhatsApp number is not ADMIN/OWNER of selected Channel")
    print("WAHA Channel admin check passed")


def fmt(job):
    """Owner-approved WhatsApp post format, without invented fields or extra promos."""
    page = str(job.get("page") or "")
    if not PAGE_RE.fullmatch(page):
        raise ValueError("Invalid published job page")
    def clean(value, limit=160):
        return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]
    company = clean(job.get("company"), 80).replace("*", "")
    role = clean(job.get("role"), 150)
    if not company or not role:
        raise ValueError("Company and role are required")
    qualification = clean(job.get("qualification"), 140)
    if not qualification or qualification.casefold() in ("n/a", "na", "not specified"):
        # Same eligibility extraction already used by the verified Telegram publisher.
        from post_telegram import compact_qualification
        qualification = clean(compact_qualification(job), 140)
    if not qualification:
        qualification = "Refer to official job eligibility"
    experience = clean(job.get("expYears"), 160)
    if not experience or experience.casefold() in ("n/a", "na", "not specified"):
        experience = ("Freshers eligible" if
                      str(job.get("expType") or "").lower() == "fresher"
                      else "Refer to official job posting")
    location = clean(job.get("loc"), 120) or "Refer to official job posting"
    return "\n".join([
        f"*{company} is Hiring ✅*",
        "",
        f"Role: {role}",
        f"Qualification: {qualification}",
        f"Experience: {experience}",
        f"Location: {location}",
        "",
        f"Apply Link: https://hdcareers.in/{page}",
        "",
        "💚 *WhatsApp:* https://whatsapp.com/channel/0029VbAxOna7NoZvhuKX362z",
        "✈️ *Telegram:* https://t.me/HD_Careers",
    ])


def select(doc,tg,jobs,at,run_id):
    """Pure claim selection; never backfill before activation or claim an old page twice."""
    if not doc.get("activationAt"):
        doc["activationAt"]=at
        return None
    started=parse(doc["activationAt"])
    if not started:raise ValueError("Invalid Channel activationAt")
    items=doc.setdefault("items",{})
    records=[]
    if not isinstance(tg,dict) or not isinstance(items,dict):
        raise ValueError("Unexpected delivery ledger type")
    for row in tg.values():
        if not isinstance(row,dict) or row.get("status")!="delivered":continue
        if row.get("channel")!="@HD_Careers" or not row.get("messageId"):continue
        page=str(row.get("page") or "")
        if not PAGE_RE.fullmatch(page):continue
        stamp=parse(row.get("deliveredAt"))
        if stamp and stamp>started:records.append((stamp,page,row))
    for _,page,receipt in sorted(records,key=lambda t:t[0]):
        if page in items:continue
        job=jobs.get(page)
        if not job or job.get("status")!="active":
            items[page]={"status":"skipped_inactive","at":at}
            continue
        items[page]={"status":"sending","claimId":run_id,"at":at,
                     "telegramMessageId":receipt["messageId"],
                     "telegramDeliveredAt":receipt["deliveredAt"]}
        return page
    return None


def claim():
    if os.getenv("WAHA_CHANNEL_ENABLED","").lower()!="true":
        print("WAHA Channel mirror disabled; nothing sent")
        return
    configured_channel()
    configured_endpoint()
    run=os.getenv("GITHUB_RUN_ID","").strip()
    if not run:raise RuntimeError("GITHUB_RUN_ID required for at-most-once claim")
    doc=load(LEDGER,{"version":1,"activationAt":None,"items":{}})
    if doc.get("version")!=1 or not isinstance(doc.get("items"),dict):
        raise RuntimeError("Invalid Channel delivery ledger")
    jobs={str(j.get("page")):j for j in load(JOBS,[]) if isinstance(j,dict)}
    page=select(doc,load(TG,{}),jobs,utc(),run)
    save(LEDGER,doc)
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"],"a",encoding="utf-8") as stream:
            stream.write("claimed="+("true" if page else "false")+"\n")
    print("WAHA Channel selected:",page or "none (activated or no new Telegram receipt)")


def provider_message_id(result):
    """WAHA may return string or object message IDs depending on its engine."""
    if not isinstance(result,dict):return None
    msg=result.get("message") if isinstance(result.get("message"),dict) else result
    candidate=msg.get("id")
    if isinstance(candidate,str) and candidate.strip():return candidate.strip()
    if isinstance(candidate,dict):
        value=candidate.get("_serialized") or candidate.get("id")
        if isinstance(value,str) and value.strip():return value.strip()
    return None


def send():
    if os.getenv("WAHA_CHANNEL_ENABLED","").lower()!="true":
        raise RuntimeError("WAHA Channel mirror disabled")
    doc=load(LEDGER,{})
    run=os.getenv("GITHUB_RUN_ID","")
    matches=[(p,v) for p,v in doc.get("items",{}).items()
             if isinstance(v,dict) and v.get("claimId")==run and v.get("status")=="sending"]
    if len(matches)!=1:raise RuntimeError("No unique precommitted WhatsApp claim")
    page,entry=matches[0]
    try:
        jobs={j.get("page"):j for j in load(JOBS,[]) if isinstance(j,dict)}
        job=jobs.get(page)
        if not job or job.get("status")!="active":
            entry.update(status="skipped_inactive",checkedAt=utc());return
        from check_job_availability import check
        verdict=check(job)
        if verdict.get("state")!="active":
            entry.update(status="skipped_unverified",checkState=verdict.get("state","review"),checkedAt=utc());return
        from publish_verified_telegram import live_job
        if not live_job(job):
            entry.update(status="skipped_site_unavailable",checkedAt=utc());return
        verify_admin()
        result=api("/api/sendText","POST",{
            "session":configured_session(),
            "chatId":configured_channel(),
            "text":fmt(job),"linkPreview":True})
        mid=provider_message_id(result)
        if not mid:raise RuntimeError("WAHA returned no confirmed post ID")
        entry.update(status="provider_accepted",providerMessageId=mid,
                     acceptedAt=utc(),provider="WAHA",channelId=configured_channel())
        print("WAHA accepted Channel post",page,"message-id",mid[:70])
    except Exception as err:
        if entry.get("status")=="sending":
            entry.update(status="uncertain",failedAt=utc(),errorType=type(err).__name__)
        print("WAHA outcome needs manual reconciliation:",page,type(err).__name__,file=sys.stderr)
        raise
    finally:
        save(LEDGER,doc)


def main():
    if len(sys.argv)!=2 or sys.argv[1] not in ("claim","send","verify"):
        raise SystemExit("Usage: whatsapp_channel_relay.py claim|send|verify")
    {"claim":claim,"send":send,"verify":verify_admin}[sys.argv[1]]()


if __name__=="__main__":main()
