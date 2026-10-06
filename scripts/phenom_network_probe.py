#!/usr/bin/env python3
import json, re, sys
from pathlib import Path
from urllib.parse import urlsplit
sys.path.insert(0, str(Path(__file__).resolve().parent))
from job_verifier_v2 import UA, safe_url

JOBISH=re.compile(r"job|requisition|position|posting|apply|career|candidate|search", re.I)
PHENOM=re.compile(r"phenompeople|phenom\.com|phncdn|phn-", re.I)

def probe(job):
    from playwright.sync_api import sync_playwright
    url=job["apply"]; safe_url(url)
    events=[]
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True)
        page=b.new_page(user_agent=UA)
        def capture(r):
            u=r.url
            if PHENOM.search(u) or JOBISH.search(urlsplit(u).path+"?"+urlsplit(u).query):
                events.append({"status":r.status,"url":u,"contentType":r.headers.get("content-type","")})
        page.on("response",capture)
        try:
            page.goto(url,wait_until="domcontentloaded",timeout=25000)
            page.wait_for_timeout(2200)
            text=page.locator("body").inner_text(timeout=5000)
            out={"id":job["id"],"company":job["company"],"role":job["role"],"manualGroundTruth":job["manualGroundTruth"],"final_url":page.url,"title":page.title(),"body":text[:1800],"network":events[:80]}
        except Exception as e:
            out={"id":job["id"],"company":job["company"],"error":type(e).__name__,"network":events[:80]}
        b.close()
    return out

jobs=json.load(open(sys.argv[1]))
for j in jobs:
    print(json.dumps(probe(j),ensure_ascii=False))
