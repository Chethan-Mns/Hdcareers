#!/usr/bin/env python3
"""Fail closed if an HD Careers Reel is not ready to publish.

Preflight is intentionally separate from the rendering step. A failed audio,
footage, sync, rights or Auto-DM step must NEVER quietly publish another video.
"""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit


def validate(manifest:dict,status:dict,video:Path, *,
             commercial_required:bool=True, binding:dict|None=None,
             binding_required:bool=False)->list[str]:
    errors=[]
    if status.get("status")!="rendered":errors.append("Reel has not been rendered")
    if status.get("captionSync")!="source_word_timestamps":errors.append("Voice captions not timestamp-synced")
    if status.get("voiceEngine")!="elevenlabs":errors.append("Selected Sarah voice was not used")
    if not status.get("employerLogoFound"):errors.append("Approved employer logo missing")
    seconds=status.get("durationSeconds")
    if not isinstance(seconds,(int,float)) or not 8<=seconds<=16:
        errors.append("Reel duration outside the allowed short-video window")
    if commercial_required and not status.get("audioCommercialRightsVerified"):
        errors.append("ElevenLabs audio commercial-use rights not confirmed")
    if not video.is_file() or video.stat().st_size<100000:
        errors.append("Rendered MP4 is missing")
    if not str(manifest.get("company") or "").strip() or not str(manifest.get("role") or "").strip():
        errors.append("Employer or job role missing")
    job_id=manifest.get("jobId")
    url=str(manifest.get("jobUrl") or "")
    p=urlsplit(url)
    if not job_id or not re.fullmatch(r"/jobs/[a-z0-9-]+\.html",p.path) \
       or p.scheme!="https" or p.netloc!="hdcareers.in" or p.query or p.fragment:
        errors.append("Unverified HD Careers job URL")
    if binding_required:
        if not isinstance(binding,dict):
            errors.append("No job-specific SuperProfile Auto-DM receipt")
        else:
            if str(binding.get("jobId"))!=str(job_id) or binding.get("jobUrl")!=url:
                errors.append("SuperProfile binding refers to a different job")
            if binding.get("instagramAccount")!="hd_careers":
                errors.append("SuperProfile binding refers to wrong Instagram account")
            dm=binding.get("autoDm") or {}
            if dm.get("matchMode")!="any" or dm.get("delaySeconds")!=30 or dm.get("followGate") is not True:
                errors.append("SuperProfile Auto-DM not armed for any-comment, 30s, follow request")
            if binding.get("state") not in ("armed","scheduled"):
                errors.append("SuperProfile link DM is not armed")
            if not re.fullmatch(r"[a-f0-9]{24}",str(binding.get("postId") or "")):
                errors.append("SuperProfile scheduled Reel post ID is missing")
    return errors


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",default="artifacts/reel/manifest.json")
    ap.add_argument("--status",default="artifacts/reel/status.json")
    ap.add_argument("--video",default="artifacts/reel/reel.mp4")
    ap.add_argument("--require-commercial-license",action="store_true")
    ap.add_argument("--require-superprofile-binding",default="")
    args=ap.parse_args()
    manifest=json.loads(Path(args.manifest).read_text())
    status=json.loads(Path(args.status).read_text())
    binding_file=Path(args.require_superprofile_binding) if args.require_superprofile_binding else None
    binding=json.loads(binding_file.read_text()) if binding_file and binding_file.exists() else None
    problems=validate(manifest,status,Path(args.video),
                      commercial_required=args.require_commercial_license,
                      binding=binding,binding_required=bool(binding_file))
    if problems:
        for problem in problems:print("NOT READY: "+problem)
        raise SystemExit("Reel held; no Instagram publishing")
    print("Reel preflight passed")


if __name__=="__main__":
    main()
