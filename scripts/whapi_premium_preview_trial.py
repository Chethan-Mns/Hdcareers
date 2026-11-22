#!/usr/bin/env python3
"""One-post HD Careers premium OG card trial. Not a global image rollout.

This only modifies the already published Synopsys job page selected as the
next scheduled Telegram/WhatsApp job on 22 Nov 2026. It never sends messages.
The image and HTML are committed BEFORE WhatsApp sees the public job URL.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
PAGE = "jobs/synopsys-cad-design-support-apprenticeship.html"
IMAGE = "assets/job-previews/synopsys-cad-design-support-apprenticeship.png"
TRIAL = "data/whapi-preview-trial.json"
PUBLIC_IMAGE = "https://hdcareers.in/" + IMAGE
PUBLIC_JOB = "https://hdcareers.in/" + PAGE
SIZE = (1200, 630)
MAX_FILE_SIZE = 800_000


def font(size: int, bold: bool = False):
    names = (
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"]
        if bold else
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"]
    )
    for name in names:
        if Path(name).is_file():
            return ImageFont.truetype(name, size)
    raise RuntimeError("A suitable TrueType font is required to render the card")


def fit_lines(draw, text: str, max_width: int, max_lines: int = 2):
    words = str(text).split()
    for size in range(61, 35, -2):
        f = font(size, bold=True)
        lines = []
        line = ""
        for word in words:
            candidate = (line + " " + word).strip()
            if draw.textbbox((0, 0), candidate, font=f)[2] <= max_width:
                line = candidate
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)
        if len(lines) <= max_lines and all(
            draw.textbbox((0, 0), part, font=f)[2] <= max_width for part in lines
        ):
            return f, lines
    raise ValueError("Role text too long for approved preview layout")


def center(draw, y, label, f, fill):
    bounds = draw.textbbox((0, 0), label, font=f)
    w = bounds[2] - bounds[0]
    draw.text(((1200 - w) // 2, y), label, fill=fill, font=f)


def load_job_and_logo(root=ROOT):
    jobs = json.loads((root / "data/jobs.json").read_text(encoding="utf-8"))
    matches = [j for j in jobs if isinstance(j, dict) and j.get("page") == PAGE]
    if len(matches) != 1:
        raise RuntimeError("Expected exactly one original Synopsys job")
    job = matches[0]
    if job.get("status") != "active" or job.get("company") != "Synopsys":
        raise RuntimeError("Target job is no longer active or company changed")
    if "Apprenticeship" not in str(job.get("role") or ""):
        raise RuntimeError("Target job role changed; refuse to guess new content")
    logos = json.loads((root / "data/company-logos.json").read_text(encoding="utf-8"))
    logo_info = logos.get("Synopsys", {})
    logo_rel = str(logo_info.get("localPath", ""))
    if not re.fullmatch(r"assets/company-icons/[a-z0-9-]+\.png", logo_rel):
        raise RuntimeError("Official Synopsys PNG logo must exist locally")
    if not str(logo_info.get("sourceType", "")).startswith("official"):
        raise RuntimeError("Only the verified official logo is allowed in this trial")
    logo_path = root / logo_rel
    if not logo_path.is_file():
        raise RuntimeError("Verified logo asset missing from repository")
    return job, logo_path


def check_next_job(root=ROOT):
    queue = json.loads((root / "data/telegram-hourly-queue.json").read_text(encoding="utf-8"))
    pending = [x for x in queue.get("items", []) if x.get("status") == "pending"]
    pending.sort(key=lambda x: str(x.get("dueAt") or "9999"))
    if not pending or pending[0].get("page") != PAGE:
        raise RuntimeError("The next scheduled Telegram job is no longer Synopsys; abort one-off image trial")
    receipts = json.loads((root / "data/whatsapp-channel-deliveries.json").read_text(encoding="utf-8"))
    if PAGE in receipts.get("items", {}):
        raise RuntimeError("Synopsys WhatsApp post already claimed: no retrospective preview edit")
    return pending[0]["dueAt"]


def render(job, logo_path, output: Path):
    image = Image.new("RGB", SIZE, "#f4f9ff")
    d = ImageDraw.Draw(image)
    # Subtle premium white-to-blue base plus corner brand decorations.
    for y in range(630):
        blend = y / 630.0
        d.line((0, y, 1200, y),
               fill=(int(250 - 13 * blend), int(252 - 10 * blend), 255))
    d.ellipse((-320, -260, 400, 450), fill="#e1f1ff")
    d.ellipse((925, -320, 1550, 310), fill="#d7eaff")
    d.polygon([(1125, 0), (1200, 0), (1200, 330), (920, 0)], fill="#b9ddff")
    d.rounded_rectangle((388, 30, 812, 185), radius=24,
                        fill="#ffffff", outline="#c9e1fb", width=3)
    with Image.open(logo_path) as raw:
        logo = raw.convert("RGBA")
        logo.thumbnail((380, 132), Image.Resampling.LANCZOS)
        image.paste(logo, ((1200 - logo.width)//2, 107 - logo.height//2), logo)
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((481, 205, 719, 258), radius=27, fill="#0668dc")
    center(d, 218, "HIRING NOW", font(24, True), "#ffffff")
    role = str(job["role"]).strip()
    f, lines = fit_lines(d, role, 990)
    line_step = f.size + 11
    y = 290 if len(lines) == 2 else 314
    for line in lines:
        center(d, y, line, f, "#081c40")
        y += line_step
    # Compact badges chosen from verified job fields only.
    location = str(job.get("loc") or "").split(",")[0].strip() or "India"
    chips = [location, "Apprenticeship"]
    chipfont = font(25, True)
    widths = [d.textbbox((0, 0), word, font=chipfont)[2] + 62 for word in chips]
    total = sum(widths) + 22
    cursor = (1200 - total) // 2
    for label, width in zip(chips, widths):
        d.rounded_rectangle((cursor, 474, cursor + width, 522),
                            radius=24, fill="#ffffff", outline="#c7ddf4", width=2)
        d.text((cursor+30, 480), label, font=chipfont, fill="#17427b")
        cursor += width + 22
    d.rounded_rectangle((0, 552, 1200, 658), radius=0, fill="#08275a")
    d.rounded_rectangle((436, 566, 764, 615), radius=12, fill="#126fe7")
    center(d, 575, "HD CAREERS", font(28, True), "#ffffff")
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG", optimize=True)
    if output.stat().st_size >= MAX_FILE_SIZE:
        raise RuntimeError("Preview PNG exceeds size budget")
    if output.stat().st_size <= 5_000:
        raise RuntimeError("Preview PNG unexpectedly small")
    with Image.open(output) as check:
        if check.size != SIZE or check.format != "PNG":
            raise RuntimeError("Preview image format/dimensions are incorrect")
    print("Generated official-logo premium OG preview", output, output.stat().st_size, "bytes")


def inject_meta(html: str) -> str:
    anchor = '<meta property="og:url" content="' + PUBLIC_JOB + '">'
    if html.count(anchor) != 1:
        raise RuntimeError("Expected exact Synopsys page og:url anchor")
    if 'property="og:image"' in html or '<!-- One-post premium WhatsApp trial' in html:
        raise RuntimeError("This page already has a preview trial; do not change again")
    tags = "\n".join([
        '<!-- One-post premium WhatsApp trial; owner approval needed before a global rollout -->',
        '<meta property="og:image" content="' + PUBLIC_IMAGE + '">',
        '<meta property="og:image:secure_url" content="' + PUBLIC_IMAGE + '">',
        '<meta property="og:image:type" content="image/png">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta property="og:image:alt" content="Synopsys CAD / Design Support Apprenticeship hiring card by HD Careers">',
        '<meta name="twitter:card" content="summary_large_image">',
        '<meta name="twitter:image" content="' + PUBLIC_IMAGE + '">',
    ])
    return html.replace(anchor, anchor + "\n" + tags, 1)


def main():
    job, logo = load_job_and_logo()
    due = check_next_job()
    output = ROOT / IMAGE
    pagefile = ROOT / PAGE
    html = pagefile.read_text(encoding="utf-8")
    proposed = inject_meta(html)
    render(job, logo, output)
    pagefile.write_text(proposed, encoding="utf-8")
    state = {
        "version": 1,
        "mode": "one-post-preview-trial",
        "status": "card_committed_pending_public_deployment",
        "jobPage": PAGE,
        "company": "Synopsys",
        "imagePath": IMAGE,
        "previewImageUrl": PUBLIC_IMAGE,
        "scheduledTelegramDueAt": due,
        "globalRollout": False,
        "approvalRequired": True,
        "note": "Only the Synopsys link preview is changed. Whapi message text and all other job pages remain untouched.",
    }
    (ROOT / TRIAL).write_text(json.dumps(state, indent=2)+"\n", encoding="utf-8")
    print("Prepared ONE job page, no WhatsApp/Telegram post was sent")


if __name__ == "__main__":
    main()
