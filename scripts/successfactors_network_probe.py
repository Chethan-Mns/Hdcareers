#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/154 Safari/537.36"
RX=re.compile(r"successfactors|career|jobreq|requisition|jobdetail|apply|position",re.I)

def probe(job):
    hits=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(user_agent=UA)
        def on_response(r):
            if not RX.search(r.url):
                return
            item={"status":r.status,"url":r.url}
            try:
                ct=r.headers.get("content-type","")
                if "json" in ct or "text" in ct or "javascript" in ct:
                    raw=r.text()
                    item["body"]=raw[:5000]
            except Exception as exc:
                item["body_error"]=type(exc).__name__
            hits.append(item)
        page.on("response",on_response)
        try:
            page.goto(job["apply"],wait_until="domcontentloaded",timeout=30000)
            page.wait_for_timeout(4000)
            body=page.locator("body").inner_text(timeout=5000)
            final=page.url
        except Exception as exc:
            body=""
            final=page.url
            hits.append({"navigation_error":type(exc).__name__})
        browser.close()
    return {"id":job.get("id"),"company":job.get("company"),"role":job.get("role"),"manualGroundTruth":job.get("manualGroundTruth"),"final_url":final,"body":body[:1500],"network":hits}

def main():
    jobs=json.loads(Path(sys.argv[1]).read_text())
    for job in jobs:
        if job.get("company") not in {"HCLTech","Wipro"}:
            continue
        print(json.dumps(probe(job),ensure_ascii=False))

if __name__=="__main__":
    main()
