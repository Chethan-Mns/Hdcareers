#!/usr/bin/env python3
"""Create a per-Reel SuperProfile Auto-DM handoff draft; never publish or send.

SuperProfile scheduling with attached post-specific Auto-DM currently requires
a paid plan. This artifact works as a prepared, reviewable manual handoff
for the free comment-to-DM product too.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

PAGE_RE = re.compile(r"^/jobs/[a-z0-9-]+\.html$")


def draft(manifest: dict) -> dict:
    if not isinstance(manifest, dict):
        raise ValueError("Expected a Reel manifest object")
    page = str(manifest.get("page") or "").strip().lstrip("/")
    url = str(manifest.get("jobUrl") or "").strip()
    p = urlsplit(url)
    if (
        not re.fullmatch(r"jobs/[a-z0-9-]+\.html", page)
        or p.scheme != "https" or p.netloc != "hdcareers.in"
        or p.path != "/" + page or p.query or p.fragment
    ):
        raise ValueError("SuperProfile link must be the verified HD Careers job page")
    if not str(manifest.get("caption") or "").find("APPLY") >= 0:
        raise ValueError("Reel caption must invite the matching APPLY keyword")
    if not manifest.get("jobId") or not manifest.get("company") or not manifest.get("role"):
        raise ValueError("Reel manifest is missing job identity")
    return {
        "version": 1,
        "state": "draft_not_connected",
        "platform": "instagram",
        "postType": "reel",
        "jobId": manifest["jobId"],
        "company": manifest["company"],
        "role": manifest["role"],
        "jobUrl": url,
        "matchMode": "keywords",
        "keyword": "APPLY",
        "postScope": "specific_reel",
        "openingMessage": "Thanks for checking out this job on HD Careers! Tap below for the job details and official application link.",
        "buttonText": "View Job",
        "buttonUrl": url,
        "followGate": False,
        "automatedMessageEnabled": False,
        "instructions": [
            "Review this draft alongside the approved Instagram Reel.",
            "Connect the HD Careers Instagram professional account to SuperProfile Auto-DM.",
            "On SuperProfile free: attach APPLY keyword to this exact published Reel and paste this job-specific link manually.",
            "On paid SuperProfile scheduling: attach the Auto-DM draft to the scheduled Reel before publishing.",
            "Test with an opted-in Instagram account before activating. Never assume a DM was delivered.",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="artifacts/reel/manifest.json")
    parser.add_argument("--output", default="artifacts/reel/superprofile-autodm-draft.json")
    args = parser.parse_args()
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(draft(data), ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print("Prepared SuperProfile draft only; no Instagram message was sent")


if __name__ == "__main__":
    main()
