#!/usr/bin/env python3
"""HD Careers daily Reel factory: verified-job selection and media rendering.

Safe default: create a storyboard and caption only. Rendering requires owner
footage and ElevenLabs credentials; publishing is handled separately.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
import re
import subprocess
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://hdcareers.in/"
BRANDS = {"Deloitte": 17, "EY": 15, "Infosys": 16, "Microsoft": 16, "Google": 16,
          "Amazon": 16, "Cisco": 15, "Accenture": 15, "Oracle": 14, "Adobe": 14,
          "Visa": 13, "Mastercard": 13, "Stripe": 13, "Salesforce": 14, "IBM": 13}
EXCLUDE_ROLES = re.compile(r"\b(senior|lead|principal|manager|director|architect)\b", re.I)
ALLOWED_EXTS = {".mp4", ".mov", ".m4v"}


def read_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def parse_time(raw):
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def choose_job(jobs, availability, already, requested=None, now=None):
    now = now or datetime.now(timezone.utc)
    checked = {str(x.get("id")): x for x in availability.get("items", [])}
    eligible = []
    for job in jobs:
        if job.get("status") != "active" or job.get("expType") != "fresher":
            continue
        if job.get("field") not in ("it", "nonit"):
            continue
        if str(job.get("id")) in already:
            continue
        if EXCLUDE_ROLES.search(str(job.get("role", ""))):
            continue
        evidence = checked.get(str(job.get("id")))
        when = parse_time(evidence.get("checkedAt")) if evidence else None
        if not evidence or evidence.get("state") != "active" or not when:
            continue
        if not timedelta(0) <= now - when <= timedelta(hours=36):
            continue
        if requested is not None and int(job.get("id", 0)) != requested:
            continue
        score = BRANDS.get(str(job.get("company")), 4)
        score += 2 if job.get("field") == "it" else 0
        score += 2 if job.get("cat") in ("internship", "campus") else 0
        score += 1 if job.get("batch") not in ("", "Not Specified", "Not specified") else 0
        eligible.append((score, int(job.get("id", 0)), job))
    if not eligible:
        return None
    eligible.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return eligible[0][2]


def city_for(job):
    place = str(job.get("loc") or "India").split(",")[0].strip()
    place = re.split(r"\s*/\s*", place)[0]
    return place if len(place) < 32 else "India"


def short_role(job):
    role = str(job.get("roleTag") or job.get("role") or "entry-level")
    role = re.sub(r"\s*[-–|]\s*(?:India|Bengaluru|Hyderabad|Mumbai|Pune).*$", "", role, flags=re.I)
    return role if len(role) < 55 else role[:52].rsplit(" ", 1)[0]


def storyboard(job):
    company = str(job["company"])
    role = short_role(job)
    place = city_for(job)
    script = f"Hey guys! {company} is hiring freshers for a {role} role in {place}. Check the eligibility and comment APPLY below for the job link!"
    # Guard spoken duration; word count is an estimate, not a promise.
    if len(script.split()) > 34:
        script = f"Hey guys! {company} is hiring freshers for {role} in {place}. Interested? Comment APPLY below for the application link!"
    url = SITE + str(job["page"]).lstrip("/")
    salary = str(job.get("salary") or "Not Disclosed")
    salary_text = "Salary: " + salary if salary.lower() not in ("not disclosed", "not specified", "n/a") else "Salary: Not disclosed"
    caption = ("\U0001f6a8 " + company.upper() + " HIRING — " + role + "\n\n"
               + "\U0001f393 Fresher / early-career opportunity\n"
               + "\U0001f4cd Location: " + str(job.get("loc") or "India") + "\n"
               + "\U0001f4bc " + salary_text + "\n"
               + "\U0001f4bb " + ("IT" if job.get("field") == "it" else "Non-IT") + " opportunity\n\n"
               + "Comment APPLY for the job link.\n"
               + "Verify your exact eligibility before applying.\n\n"
               + url + "\n\n"
               + "#FresherJobs #OffCampusDrive #JobAlert #IndiaJobs #HDCareers")
    return {"jobId": job["id"], "company": company, "role": role, "location": job.get("loc"),
            "page": job["page"], "apply": job.get("apply"), "jobUrl": url,
            "script": script, "caption": caption, "status": "planned",
            "verification": "Latest official-source availability scan marked active"}


def font(size, bold=False):
    from PIL import ImageFont
    names = (["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"] if bold else [
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"])
    for name in names:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def wrap(draw, text, fnt, max_width):
    lines = []
    for paragraph in str(text).split("\n"):
        row = ""
        for word in paragraph.split():
            candidate = (row + " " + word).strip()
            if row and draw.textbbox((0, 0), candidate, font=fnt)[2] > max_width:
                lines.append(row)
                row = word
            else:
                row = candidate
        lines.append(row)
    return lines


def draw_card(job, plan, dest):
    from PIL import Image, ImageDraw
    canvas = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    blue = "#075ee9"; ink = "#091c3b"
    draw.rounded_rectangle((64, 275, 1016, 1480), radius=32, fill="white", outline="#d3dff1", width=3)
    draw.rounded_rectangle((86, 1325, 994, 1450), radius=22, fill="#dcecff")
    logo_path = ROOT / str(job.get("logoPath") or "")
    has_logo = logo_path.is_file() and str(job.get("logoPath", "")).startswith("assets/")
    if has_logo:
        try:
            with Image.open(logo_path) as raw:
                logo = raw.convert("RGBA")
                logo.thumbnail((250, 105))
                canvas.alpha_composite(logo, (110, 345))
        except (OSError, ValueError):
            has_logo = False
    if not has_logo:
        draw.text((105, 355), str(job["company"])[:22], font=font(49, bold=True), fill=blue)
    draw.text((110, 475), "HIRING FRESHERS", font=font(31, bold=True), fill=blue)
    y = 540
    for line in wrap(draw, str(job.get("roleTag") or job.get("role")), font(48, bold=True), 830)[:3]:
        draw.text((110, y), line, font=font(48, bold=True), fill=ink)
        y += 68
    draw.line((110, y + 18, 970, y + 18), fill=blue, width=4)
    info = [
        ("Company", str(job.get("company"))),
        ("Location", str(job.get("loc") or "India")),
        ("Experience", str(job.get("expYears") or "Fresher")),
        ("Category", "Fresher IT" if job.get("field") == "it" else "Fresher Non-IT"),
        ("Salary", str(job.get("salary") or "Not Disclosed"))
    ]
    y += 70
    label = font(30, bold=True); value = font(28)
    for key, val in info:
        draw.text((110, y), key, font=label, fill=ink)
        val_lines = wrap(draw, val, value, 570)
        for index, txt in enumerate(val_lines[:2]):
            draw.text((390, y + index * 37), txt, font=value, fill="#263852")
        y += max(72, 30 + len(val_lines[:2]) * 35)
    draw.text((110, 1262), "Official eligibility applies", font=font(26), fill="#3a506f")
    draw.text((120, 1355), "Comment 'APPLY' for the link", font=font(35, bold=True), fill=blue)
    dest.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dest)


def voiceover(plan, path):
    key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    voice = os.getenv("ELEVENLABS_VOICE_ID", "").strip()
    if not key or not voice:
        raise RuntimeError("ElevenLabs API key or voice ID is not configured")
    body = json.dumps({"text": plan["script"], "model_id": "eleven_flash_v2_5"}).encode("utf-8")
    req = Request("https://api.elevenlabs.io/v1/text-to-speech/" + voice + "?output_format=mp3_44100_128",
                  data=body, method="POST",
                  headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"})
    with urlopen(req, timeout=75) as response:
        data = response.read(10_000_000)
    if not data.startswith(b"ID3") and data[:2] != b"\xff\xfb":
        # Some MP3s start with other MPEG frame headers; a minimum size still protects against JSON errors.
        if len(data) < 4096 or data.lstrip().startswith(b"{"):
            raise RuntimeError("ElevenLabs did not return playable audio")
    path.write_bytes(data)


def audio_duration(path):
    output = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                      "-of", "default=nokey=1:noprint_wrappers=1", str(path)], text=True)
    seconds = float(output.strip())
    if seconds < 3 or seconds > 45:
        raise ValueError("Unexpected voiceover duration")
    return seconds


def make_video(footage, card, voice, output):
    duration = audio_duration(voice) + 0.6
    vf = "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30[bg];[1:v]format=rgba[card];[bg][card]overlay=0:0:shortest=0[v]"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-stream_loop", "-1",
           "-i", str(footage), "-loop", "1", "-i", str(card), "-i", str(voice),
           "-filter_complex", vf, "-map", "[v]", "-map", "2:a:0",
           "-t", f"{duration:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
           "-r", "30", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000",
           "-b:a", "128k", "-movflags", "+faststart", str(output)]
    subprocess.run(cmd, check=True, timeout=240)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", type=int)
    parser.add_argument("--output-dir", default="artifacts/reel")
    parser.add_argument("--footage-dir", default="assets/reel-footage")
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    jobs = read_json(ROOT / "data/jobs.json", [])
    availability = read_json(ROOT / "data/availability-status.json", {})
    posted = read_json(ROOT / "data/reel-posts.json", [])
    already = {str(x.get("jobId")) for x in posted if x.get("status") in ("posted", "uncertain")}
    job = choose_job(jobs, availability, already, args.job_id)
    if job is None:
        (out / "status.json").write_text(json.dumps({"status": "no_eligible_verified_job",
            "message": "No fresh, confirmed-active, unposted Fresher IT / Non-IT opportunity"}, indent=2) + "\n")
        print("No eligible active job; NOTHING posted")
        return
    plan = storyboard(job)
    plan["selectedAt"] = datetime.now(timezone.utc).isoformat()
    (out / "manifest.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
    (out / "script.txt").write_text(plan["script"] + "\n")
    (out / "caption.txt").write_text(plan["caption"] + "\n")
    if not args.render:
        print("Prepared storyboard, script and caption for job", job["id"])
        return
    clips = sorted(p for p in Path(args.footage_dir).glob("*") if p.suffix.lower() in ALLOWED_EXTS and p.is_file())
    if not clips:
        (out / "status.json").write_text(json.dumps({"status": "needs_footage", "message": "Upload a reusable MP4/MOV to assets/reel-footage/"}, indent=2))
        print("No reusable footage. Storyboard ready, no video rendered.")
        return
    if not os.getenv("ELEVENLABS_API_KEY") or not os.getenv("ELEVENLABS_VOICE_ID"):
        (out / "status.json").write_text(json.dumps({"status": "needs_elevenlabs_credentials"}, indent=2))
        print("ElevenLabs not configured. No voice generated and no post attempted.")
        return
    from PIL import Image  # dependency check before billable voice request
    clip_index = int(hashlib.sha256(str(job["id"]).encode()).hexdigest()[:8], 16) % len(clips)
    card = out / "card.png"
    voice = out / "voice.mp3"
    draw_card(job, plan, card)
    voiceover(plan, voice)
    make_video(clips[clip_index], card, voice, out / "reel.mp4")
    (out / "status.json").write_text(json.dumps({"status": "rendered", "jobId": job["id"]}, indent=2))
    print("Rendered reel.mp4 for job", job["id"], "using", clips[clip_index].name)

if __name__ == "__main__":
    main()
