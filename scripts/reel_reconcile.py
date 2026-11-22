#!/usr/bin/env python3
"""Reconcile SuperProfile Reel publication receipts against GitHub ledger.

This never publishes, reschedules or sends a DM. Unknown and failed states
do not trigger automatic duplicate posting.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path

from superprofile_reel_bridge import MCP, SuperProfileError


def merge_provider_status(record:dict,post:dict)->dict:
    changed=dict(record)
    state=str(post.get("status") or "")
    pub=post.get("publish") or {}
    if str(post.get("igUsername") or "") != "hd_careers":
        raise ValueError("SuperProfile receipt refers to inactive or unknown Instagram account")
    target={
        "published":"posted", "scheduled":"scheduled",
        "publishing":"publishing", "unknown":"uncertain",
        "failed":"failed", "cancelled":"cancelled"
    }.get(state)
    if target:
        changed["status"]=target
        if target=="posted":
            changed["instagramMediaId"]=pub.get("mediaId")
            changed["instagramPermalink"]=pub.get("permalink")
            changed["publishedAt"]=pub.get("publishedAt")
        elif target in ("failed","uncertain"):
            reason=pub.get("reason") or {}
            changed["publishProblem"]=str(reason.get("title") or reason.get("detail") or state)[:200]
    return changed


def reconcile(ledger:list[dict],lookup)->tuple[list[dict],int]:
    refreshed=[]
    updates=0
    for x in ledger:
        if x.get("provider")!="superprofile" or x.get("status") not in (
             "scheduled","publishing","uncertain"):
            refreshed.append(x);continue
        post_id=x.get("superprofilePostId")
        if not post_id:
            refreshed.append(x);continue
        try:
            result=lookup(post_id)
            post=result.get("post") or {}
            item=merge_provider_status(x,post)
            if item!=x:updates+=1
            refreshed.append(item)
        except (SuperProfileError,ValueError):
            # Never invent success from a failed status check.
            refreshed.append(x)
    return refreshed,updates


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--ledger",default="data/reel-posts.json")
    args=ap.parse_args()
    path=Path(args.ledger)
    records=json.loads(path.read_text(encoding="utf-8"))
    if not any(x.get("provider")=="superprofile" and x.get("status") in
               ("scheduled","publishing","uncertain") for x in records):
        print("No pending SuperProfile reels to reconcile")
        return
    mcp=MCP(os.environ.get("SUPERPROFILE_MCP_ACCESS_TOKEN",""))
    mcp.start()
    updated,count=reconcile(records,lambda pid:mcp.tool("get_scheduled_post",{"postId":pid}))
    if count:
        path.write_text(json.dumps(updated,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(f"SuperProfile Reel publication reconciliation: {count} record(s) changed; no retry or DM sent")


if __name__=="__main__":
    main()
