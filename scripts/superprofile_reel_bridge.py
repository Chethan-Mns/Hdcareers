#!/usr/bin/env python3
"""GitHub Actions -> SuperProfile scheduling bridge for HD Careers.

A runner (unlike ChatGPT's sandbox) can PUT an MP4 to the signed upload URL
returned by SuperProfile. A separately-authorized OAuth access token is needed
for this CI worker; the ChatGPT connector's token is NOT exported here.

Sequence: check account -> reuse a matching draft -> upload video -> attach
job-specific any-comment/30-second/follow Auto-DM -> schedule >=25 min ahead.
Safe on failure: NEVER publish an Instagram Reel without its attached Auto-DM.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from zoneinfo import ZoneInfo

URL="https://mcp.superprofile.bio/mcp"
INSTAGRAM_ACCOUNT="hd_careers"
PROTOCOL_VERSION="2025-06-18"


class SuperProfileError(Exception):
    pass


class MCP:
    def __init__(self,token:str):
        if not token:raise SuperProfileError("CI SuperProfile OAuth access token not configured")
        self.token=token
        self.seq=0
        self.session=None
        self.version=PROTOCOL_VERSION

    def _post(self,method:str,params:dict|None=None,notification:bool=False):
        self.seq+=1
        payload={"jsonrpc":"2.0","method":method}
        if params is not None:payload["params"]=params
        if not notification:payload["id"]=self.seq
        headers={
            "Authorization":"Bearer "+self.token,
            "Content-Type":"application/json",
            "Accept":"application/json, text/event-stream",
            "MCP-Protocol-Version":self.version
        }
        if self.session:headers["Mcp-Session-Id"]=self.session
        request=Request(URL,data=json.dumps(payload).encode("utf8"),
                        headers=headers,method="POST")
        try:
            with urlopen(request,timeout=90) as response:
                self.session=response.headers.get("Mcp-Session-Id",self.session)
                ctype=response.headers.get("Content-Type","")
                body=response.read(2_500_000).decode("utf8")
        except HTTPError as error:
            if error.code in (401,403):
                raise SuperProfileError("SuperProfile CI OAuth token expired or lacks permissions") from None
            raise SuperProfileError(f"SuperProfile MCP HTTP {error.code} on {method}") from None
        except URLError:
            raise SuperProfileError("SuperProfile MCP transport unavailable") from None
        if notification:return {}
        if "text/event-stream" in ctype:
            events=[]
            for line in body.splitlines():
                if line.startswith("data:"):
                    try:events.append(json.loads(line[5:].strip()))
                    except ValueError:pass
            messages=[x for x in events if x.get("id")==self.seq]
            response=messages[-1] if messages else {}
        else:
            try:response=json.loads(body)
            except ValueError:raise SuperProfileError("Invalid MCP response") from None
        if response.get("error"):
            e=response["error"]
            raise SuperProfileError(f"SuperProfile {method}: {str(e.get('message','error'))[:180]}")
        return response.get("result") or {}

    def start(self):
        data=self._post("initialize",{
            "protocolVersion":self.version,
            "capabilities":{},
            "clientInfo":{"name":"hd-careers-github-reel-publisher","version":"1.0.0"}
        })
        self.version=str(data.get("protocolVersion") or self.version)
        self._post("notifications/initialized",notification=True)

    def tool(self,name:str,args:dict):
        result=self._post("tools/call",{"name":name,"arguments":args})
        if result.get("isError"):
            safe="; ".join(str(i.get("text",""))[:160] for i in result.get("content",[]) if i.get("type")=="text")
            raise SuperProfileError(f"SuperProfile {name} refused: {safe[:220]}")
        if isinstance(result.get("structuredContent"),dict):
            return result["structuredContent"]
        for item in result.get("content",[]):
            if item.get("type")=="text":
                try:return json.loads(item.get("text",""))
                except (ValueError,TypeError):pass
        return result


def unique_key(server_time:int)->str:
    return f"{int(server_time)}:{secrets.token_hex(12)}"


def exact_dm(manifest:dict)->dict:
    company=str(manifest["company"])
    role=str(manifest["role"])
    url=str(manifest["jobUrl"])
    return {
      "keywords":{"mode":"any","include":[],"exclude":[]},
      "message":f"Thanks for checking out {company} on HD Careers! 💼 {role}. Tap View Job for the official application details.",
      "buttons":[{"label":"View Job","url":url}],
      "openingMessage":{"text":f"Thanks for commenting! Want the {company} application link? Tap below 👇","button":"Get Link"},
      "followGate":{
        "openingText":"Follow @hd_careers for verified fresher opportunities! 💙",
        "openingButton":"Continue",
        "prompt":"Please follow @hd_careers, then tap I've followed to receive the application link.",
        "profileButton":"Follow","retryButton":"I've followed",
        "retry":{"maxAttempts":2,"onFailure":"stop"}
      },
      "primaryDelay":{"timeValue":30,"timeUnit":"second"}
    }


def _posts(payload:dict)->list[dict]:
    data=payload.get("posts") or payload.get("items") or payload.get("data") or []
    return data if isinstance(data,list) else []


def matching_draft(posts:list[dict],manifest:dict,ig_user_id:str)->dict|None:
    url=str(manifest["jobUrl"])
    company=str(manifest["company"]).lower()
    role=str(manifest["role"]).lower().split(",")[0]
    matches=[]
    for post in posts:
        if str(post.get("igUserId"))!=str(ig_user_id) or post.get("type")!="reel":
            continue
        caption=str(post.get("caption") or "").lower()
        if url.lower() in caption or (
           company in caption and role in caption and post.get("status") in ("draft","scheduled")
        ):
            matches.append(post)
    if len(matches)>1:
        raise SuperProfileError("Multiple matching Reel drafts; refusing duplicate publication")
    return matches[0] if matches else None


def upload_video(mcp:MCP,post:dict,video:Path)->dict:
    size=video.stat().st_size
    if size<100000 or size>314_572_800:
        raise SuperProfileError("Video size outside SuperProfile MP4 range")
    start=mcp.tool("prepare_scheduled_post_media_upload",{
        "postId":post["id"],"kind":"video","mime":"video/mp4",
        "bytes":size,"fileName":video.name
    })
    signed_url=start.get("uploadUrl")
    if not signed_url or not signed_url.startswith("https://"):
        raise SuperProfileError("SuperProfile did not return a signed video upload URL")
    # Signed requests must use the exact method and headers issued by SuperProfile.
    data=video.read_bytes()
    headers=start.get("headers") or {}
    request=Request(signed_url,data=data,headers=headers,method=start.get("method","PUT"))
    try:
        with urlopen(request,timeout=180) as reply:reply.read(512)
    except HTTPError as e:
        raise SuperProfileError(f"Video store refused upload: HTTP {e.code}") from None
    except URLError:
        raise SuperProfileError("Video upload endpoint unavailable") from None
    return mcp.tool("confirm_scheduled_post_media",{
        "postId":post["id"],"uploadId":start["uploadId"],
        "expectedRevision":int(start["expectedRevision"])
    })


def schedule(manifest:dict,status:dict,video:Path,mcp:MCP)->dict:
    from reel_preflight import validate
    errors=validate(manifest,status,video,commercial_required=True)
    if errors:
        raise SuperProfileError("Publishing safety checks failed: "+"; ".join(errors))
    context=mcp.tool("get_instagram_schedule_context",{})
    accounts=[x for x in context.get("accounts",[]) if x.get("username")==INSTAGRAM_ACCOUNT]
    if len(accounts)!=1 or not accounts[0].get("canPublish"):
        raise SuperProfileError("Active @hd_careers cannot publish in SuperProfile")
    account=accounts[0]
    if not context.get("plan",{}).get("canSchedule"):
        raise SuperProfileError("SuperProfile plan cannot schedule Reels")
    timestamp=context.get("serverTime") or int(time.time()*1000)
    now=datetime.now(ZoneInfo("Asia/Kolkata"))
    earlier=(now-timedelta(days=1)).isoformat()
    later=(now+timedelta(days=30)).isoformat()
    existing=_posts(mcp.tool("list_scheduled_posts",{"from":earlier,"to":later}))
    post=matching_draft(existing,manifest,account["igUserId"])
    if post and post.get("status") in ("scheduled","published","publishing","unknown"):
        # We never schedule duplicate posts or retry an uncertain publish.
        raise SuperProfileError("Matching Reel already scheduled or published; no duplicate created")
    if post is None:
        created=mcp.tool("prepare_scheduled_post",{
            "integrationId":account["integrationId"],"type":"reel",
            "idempotencyKey":unique_key(timestamp),
            "caption":manifest["caption"],"timezone":"Asia/Kolkata",
            "reel":{"shareToFeed":True,"trial":None}
        })
        post=created.get("post") or {}
    if not post.get("id"):
        raise SuperProfileError("SuperProfile did not create an Instagram Reel draft")
    # Only change incomplete drafts. The owner's caption should match the job.
    if not post.get("media"):
        result=upload_video(mcp,post,video)
        post=result.get("post") or mcp.tool("get_scheduled_post",{"postId":post["id"]}).get("post") or {}
    if len(post.get("media") or [])!=1:
        raise SuperProfileError("SuperProfile Reel must have exactly one video")
    if not (post.get("autoDm") or {}).get("autoDmId"):
        attached=mcp.tool("attach_auto_dm_to_scheduled_post",{
            "postId":post["id"],"expectedRevision":int(post["revision"]),
            "autoDm":exact_dm(manifest)
        })
        post=attached.get("post") or mcp.tool("get_scheduled_post",{"postId":post["id"]}).get("post") or {}
    # If another automation was previously attached, verify it matches THIS job.
    auto=post.get("autoDm") or {}
    if not auto.get("autoDmId"):
        raise SuperProfileError("Auto-DM missing; will not publish")
    live=mcp.tool("get_automation",{"automationId":auto["autoDmId"]})
    spec=live.get("spec") or {}
    buttons=(spec.get("message") or {}).get("buttons") or []
    delay=spec.get("primaryDelay") or {}
    if (spec.get("keywords") or {}).get("mode")!="any" \
       or delay.get("timeValue")!=30 or delay.get("timeUnit")!="second" \
       or not spec.get("followGate") \
       or not any(b.get("url")==manifest["jobUrl"] for b in buttons):
        raise SuperProfileError("Attached Auto-DM does not match this job, comment trigger, 30s delay or follow gate")
    # Keep >=15 min video processing + >=10 min Auto-DM lead time.
    when=(datetime.now(ZoneInfo("Asia/Kolkata"))+timedelta(minutes=30)).replace(second=0,microsecond=0)
    result=mcp.tool("schedule_post",{
        "postId":post["id"],"expectedRevision":int(post["revision"]),
        "scheduledAt":when.isoformat(timespec="seconds"),
        "timezone":"Asia/Kolkata"
    })
    updated=result.get("post") or mcp.tool("get_scheduled_post",{"postId":post["id"]}).get("post") or {}
    if updated.get("status")!="scheduled":
        raise SuperProfileError("SuperProfile scheduling not confirmed; reconcile before retry")
    return {"jobId":manifest["jobId"],"jobUrl":manifest["jobUrl"],"state":"scheduled",
            "postId":post["id"],"instagramAccount":INSTAGRAM_ACCOUNT,
            "scheduledAt":updated.get("scheduledAt") or when.isoformat(),
            "autoDm":{"matchMode":"any","delaySeconds":30,"followGate":True,"autoDmId":auto["autoDmId"]}}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",default="artifacts/reel/manifest.json")
    p.add_argument("--status",default="artifacts/reel/status.json")
    p.add_argument("--video",default="artifacts/reel/reel.mp4")
    p.add_argument("--out",default="artifacts/reel/superprofile-post-receipt.json")
    args=p.parse_args()
    manifest=json.loads(Path(args.manifest).read_text())
    status=json.loads(Path(args.status).read_text())
    mcp=MCP(os.getenv("SUPERPROFILE_MCP_ACCESS_TOKEN",""))
    mcp.start()
    receipt=schedule(manifest,status,Path(args.video),mcp)
    path=Path(args.out);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("SuperProfile scheduled Reel with any-comment 30-second follow-gated Auto-DM:",receipt["postId"])


if __name__=="__main__":
    main()
