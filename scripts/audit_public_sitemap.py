#!/usr/bin/env python3
"""External HTTP audit of every public sitemap URL. Does not alter production."""
from __future__ import annotations
import concurrent.futures
import json
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://hdcareers.in"
HEADERS = {"User-Agent": "HD-Careers-Readiness-Audit/1.0 (public sitemap, read only)"}

def get(url: str):
    try:
        with urlopen(Request(url, headers=HEADERS), timeout=18) as response:
            data = response.read(800_000)
            return {"status": response.status, "final_url": response.geturl(),
                    "body": data.decode("utf-8", errors="replace")}
    except HTTPError as exc:
        return {"status": exc.code, "error": str(exc)}
    except (URLError, TimeoutError, OSError) as exc:
        return {"status": None, "error": str(exc)}

def one(url):
    result = get(url)
    body = result.pop("body", "")
    result["url"] = url
    result["is_html"] = "<html" in body[:1500].lower()
    if result.get("status") == 200:
        result["title"] = bool(re.search(r"<title[^>]*>.+?</title>", body, re.I | re.S))
        result["canonical"] = bool(re.search(r'<link[^>]+rel=["\x27]canonical', body, re.I))
        result["noindex"] = bool(re.search(r'<meta[^>]+content=["\x27][^"\x27]*noindex', body, re.I))
    result["pass"] = (result.get("status") == 200 and result["is_html"]
                      and result.get("title") and result.get("canonical") and not result.get("noindex"))
    return result

def main():
    expected = json.loads((ROOT / "data" / "insights-summary.json").read_text(encoding="utf-8"))["active"]
    marker = f'id="hdpJobs">{expected}</b>'
    # CDN/production deployment can lag behind the GitHub push. Check the
    # expected server-rendered HTML before crawling the current release.
    ready = False
    for _ in range(16):
        page = get(ORIGIN + "/")
        if page.get("status") == 200 and marker in page.get("body", ""):
            ready = True
            break
        time.sleep(8)
    pages = get(ORIGIN + "/sitemap.xml")
    if pages.get("status") != 200:
        print(json.dumps({"error": "sitemap fetch failed", "response": pages}, ensure_ascii=False)[:1800])
        return 2
    root = ElementTree.fromstring(pages["body"])
    urls = [e.text for e in root.findall(".//{*}loc") if e.text]
    if not urls:
        print("Sitemap contains no URLs")
        return 2
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        reports = list(pool.map(one, urls))
    robots = get(ORIGIN + "/robots.txt")
    failures = [r for r in reports if not r["pass"]]
    report = {"expected_generated_homepage": ready, "urls_checked": len(reports),
              "passed": len(reports) - len(failures), "failed": len(failures),
              "robots_status": robots.get("status"),
              "robots_sitemap": "Sitemap: https://hdcareers.in/sitemap.xml" in robots.get("body", ""),
              "failures": failures, "entries": reports}
    path = ROOT / "adsense-crawl-report.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "entries"}, indent=2)[:12000])
    return 0 if ready and not failures and len(reports) >= 160 and report["robots_status"] == 200 else 1

if __name__ == "__main__":
    sys.exit(main())
