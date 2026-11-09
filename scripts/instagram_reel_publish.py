#!/usr/bin/env python3
"""Owner-authorized Instagram Professional Reel publishing."""
import argparse
import json
import os
import time
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError

def call(url,post=None):
    data=urlencode(post).encode() if post is not None else None
    try:
        with urlopen(Request(url,data=data,method="POST" if data is not None else "GET"),timeout=45) as response:
            return json.load(response)
    except HTTPError as error:
        raise RuntimeError("Instagram API returned HTTP "+str(error.code)) from None

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--manifest",default="artifacts/reel/manifest.json")
    parser.add_argument("--video-url",required=True)
    args=parser.parse_args()
    token=os.getenv("INSTAGRAM_ACCESS_TOKEN","")
    account=os.getenv("INSTAGRAM_ACCOUNT_ID","")
    version=os.getenv("META_GRAPH_VERSION") or "v24.0"
    if not token or not account:
        raise SystemExit("Meta account credentials not configured, no post sent.")
    if not args.video_url.startswith("https://"):
        raise SystemExit("Meta requires publicly accessible HTTPS video.")
    manifest=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    if not manifest.get("jobId") or not manifest.get("caption"):
        raise SystemExit("Missing verified reel manifest.")
    base="https://graph.facebook.com/"+version
    container=call(base+"/"+account+"/media",{
        "media_type":"REELS","video_url":args.video_url,"caption":manifest["caption"],
        "share_to_feed":"true","access_token":token}).get("id")
    if not container: raise SystemExit("No Instagram media container returned.")
    status="IN_PROGRESS"
    for _ in range(20):
        status=call(base+"/"+str(container)+"?"+urlencode({"fields":"status_code","access_token":token})).get("status_code")
        if status=="FINISHED":break
        if status in ("ERROR","EXPIRED"):raise SystemExit("Instagram container failed; do not retry blindly.")
        time.sleep(15)
    if status!="FINISHED":raise SystemExit("Instagram processing not complete; no publish request sent.")
    post=call(base+"/"+account+"/media_publish",{"creation_id":container,"access_token":token})
    media=post.get("id")
    if not media:raise SystemExit("Instagram publishing outcome uncertain: manually reconcile before retry.")
    receipt={"jobId":manifest["jobId"],"status":"posted","instagramMediaId":media,
             "publishedAt":datetime.now(timezone.utc).isoformat(),"jobUrl":manifest["jobUrl"]}
    Path("artifacts/reel/instagram-receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print("Instagram confirmed: job",manifest["jobId"],"media",media)

if __name__=="__main__":main()
