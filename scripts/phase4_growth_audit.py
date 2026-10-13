"""Phase 4 non-destructive SEO, accessibility and AdSense-readiness audit."""
from __future__ import annotations
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRUST = ("about.html", "contact.html", "privacy-policy.html", "disclaimer.html",
         "editorial-policy.html", "terms.html")


def audit(root=ROOT):
    jobs = json.loads((root / "data/jobs.json").read_text(encoding="utf-8"))
    seen = set()
    blockers, warnings = [], []
    summary = Counter()
    for job in jobs:
        rel = str(job.get("page") or "")
        if rel in seen:
            blockers.append("Duplicate page path: " + rel)
        seen.add(rel)
        if not rel.startswith("jobs/") or ".." in rel:
            blockers.append("Unsafe job page: " + rel)
            continue
        path = root / rel
        if not path.is_file():
            blockers.append("Missing generated job page: " + rel)
            continue
        html = path.read_text(encoding="utf-8")
        summary["jobPages"] += 1
        if len(html.encode("utf-8")) > 250000:
            warnings.append("Large generated page: " + rel)
        if job.get("status") == "expired":
            summary["expired"] += 1
            if re.search(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>[\s\S]*?"@type"\s*:\s*"JobPosting"', html):
                blockers.append("Expired job contains JobPosting: " + rel)
            if 'name="robots" content="noindex' not in html:
                blockers.append("Expired job still indexable: " + rel)
        else:
            summary["activeRecords"] += 1
        if '<link rel="canonical" href="https://hdcareers.in/' + rel + '">' not in html:
            blockers.append("Incorrect canonical: " + rel)
        if '<meta name="description"' not in html:
            blockers.append("Missing SEO description: " + rel)
        if '<meta name="twitter:card" content="summary">' not in html:
            warnings.append("Missing social preview: " + rel)
        if '<meta property="og:image" content=' not in html:
            warnings.append("Missing OG preview image: " + rel)
        if re.search(r'<script\b[^>]*\bsrc=["\']https://cdnjs\.cloudflare\.com/ajax/libs/(?:pdf\.js|mammoth)/', html, re.I):
            warnings.append("Eager resume parsing assets: " + rel)
        if 'Official Apply' not in html and job.get("status") == "active":
            blockers.append("Active job missing employer application link: " + rel)
        content = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", html, flags=re.I | re.S)
        content = re.sub(r"<[^>]+>", " ", content)
        words = len(content.split())
        if words < 600:
            summary["thinContentUnder600Words"] += 1
        if not job.get("employerPostedAt") and job.get("date") not in (None, "", "Not specified", "Not Specified"):
            summary["employerPostingDateUnproven"] += 1
    for file in TRUST:
        if not (root / file).exists():
            blockers.append("Missing trust page: " + file)
    for file in ("robots.txt", "sitemap.xml", "assets/analytics.js", "assets/hd-careers-logo.png"):
        if not (root / file).exists():
            blockers.append("Missing website asset: " + file)
    if (root / "sitemap.xml").is_file():
        sitemap = (root / "sitemap.xml").read_text(encoding="utf-8")
        for job in jobs:
            url = "https://hdcareers.in/" + str(job.get("page", ""))
            if job.get("status") == "expired" and url in sitemap:
                blockers.append("Expired job in sitemap: " + str(job["id"]))
    if (root / "assets/analytics.js").is_file():
        analytics = (root / "assets/analytics.js").read_text(encoding="utf-8")
        if 'hd_analytics_optout' not in analytics:
            blockers.append("Analytics opt-out check missing")
        if "window.location.search" in analytics:
            warnings.append("Analytics code references search query parameters")
        if "hd_web_vital" not in analytics:
            warnings.append("Aggregate page performance telemetry missing")
    if (root / "privacy-policy.html").is_file():
        privacy = (root / "privacy-policy.html").read_text(encoding="utf-8").lower()
        if "analytics" not in privacy or "cookie" not in privacy:
            warnings.append("Privacy notice needs analytics/cookie disclosure review")
    result = {"mode": "read_only", "readyForUnattendedPublishing": False,
              "websiteWritten": False, "telegramSent": False,
              "blockers": sorted(set(blockers)), "warnings": sorted(set(warnings)),
              "metrics": dict(summary),
              "adSenseApprovalGuaranteed": False}
    return result


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="phase4-growth-audit.json")
    args = p.parse_args()
    result = audit()
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"metrics": result["metrics"], "blockers": len(result["blockers"]),
                      "warnings": len(result["warnings"])}, indent=2))
    if result["blockers"]:
        raise SystemExit("Blocking SEO/trust violations: " + "; ".join(result["blockers"][:5]))


if __name__ == "__main__":
    main()
