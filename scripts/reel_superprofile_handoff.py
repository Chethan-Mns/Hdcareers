#!/usr/bin/env python3
"""Prepare a paid-plan SuperProfile Auto-DM configuration for each Reel.

Trigger on any comment on the specific Reel; request a follow, and deliver the
matching HD Careers job URL. Desired initial reply delay is 30 seconds.
This script only writes a draft: it never connects, activates, or sends a DM.
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
    if not re.search(r"comment\b", str(manifest.get("caption") or ""), re.IGNORECASE):
        raise ValueError("Reel caption must invite comments for the job link")
    if not manifest.get("jobId") or not manifest.get("company") or not manifest.get("role"):
        raise ValueError("Reel manifest is missing job identity")
    return {
        "version": 2,
        "state": "draft_not_connected",
        "platform": "instagram",
        "postType": "reel",
        "jobId": manifest["jobId"],
        "company": manifest["company"],
        "role": manifest["role"],
        "jobUrl": url,
        "matchMode": "any",
        "keyword": None,
        "delaySeconds": 30,
        "postScope": "specific_reel",
        "openingMessage": "Thanks for checking out this job on HD Careers! Tap below for the job details and official application link.",
        "buttonText": "View Job",
        "buttonUrl": url,
        "followGate": True,
        "automatedMessageEnabled": False,
        "instructions": [
            "Review this draft alongside the approved Instagram Reel.",
            "Connect the HD Careers Instagram professional account to paid SuperProfile Auto-DM.",
            "Choose this exact Brillio/job Reel; never use an all-posts trigger, because every job has a different application URL.",
            "Select Any comment (no keyword requirement), and set the initial DM time delay to 30 seconds, not 1 minute.",
            "Enable Ask to Follow before sending the job-link button, as requested by the owner.",
            "Attach the configuration before scheduling the Reel or edit the automation for an already-published Reel.",
            "A 30-second configured delay is not a guaranteed delivery SLA: Meta and SuperProfile can queue messages.",
            "Test with a consenting second Instagram account before activating; never assume a DM was delivered.",
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
