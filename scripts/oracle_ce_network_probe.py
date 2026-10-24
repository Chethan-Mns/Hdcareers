#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/154 Safari/537.36"

def probe(job):
    hits = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=UA)
        def on_response(r):
            if "hcmRestApi" not in r.url:
                return
            item = {"status": r.status, "url": r.url}
            try:
                ct = r.headers.get("content-type", "")
                if "json" in ct:
                    body = r.json()
                    raw = json.dumps(body, ensure_ascii=False)
                    item["body"] = raw[:4000]
            except Exception as exc:
                item["body_error"] = type(exc).__name__
            hits.append(item)
        page.on("response", on_response)
        try:
            page.goto(job["apply"], wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)
        except Exception as exc:
            hits.append({"navigation_error": type(exc).__name__})
        finally:
            browser.close()
    return {"id": job.get("id"), "company": job.get("company"), "role": job.get("role"), "ground_truth": job.get("status"), "network": hits}

def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "tests/fixtures/v2_oracle_live_candidates.json")
    jobs = json.loads(src.read_text())
    for job in jobs:
        print(json.dumps(probe(job), ensure_ascii=False))

if __name__ == "__main__":
    main()
