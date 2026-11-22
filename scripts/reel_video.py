#!/usr/bin/env python3
"""HD Careers: full-frame branded office footage + word-synced captions.

Produces a 9:16 MP4. The company logo is ABOVE the role; the video remains
visible behind a small top badge and lower word captions. Subtitle timing
comes from the exact audio alignment, NEVER guessed from script length.
"""
from __future__ import annotations
import json
import math
import re
import subprocess
from pathlib import Path

SIZE=(1080,1920)
MAGENTA="&H00AA4FFF"  # ASS AABBGGRR, opaque pink-magenta
WHITE="&H00FFFFFF"


def _font(size:int,bold=False):
    from PIL import ImageFont
    options=[
      "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
      "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ] if bold else [
      "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
      "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in options:
        if Path(path).exists():
            return ImageFont.truetype(path,size)
    return ImageFont.load_default()


def _company_logo(job:dict,root:Path):
    from PIL import Image
    raw=str(job.get("logoPath") or "")
    candidates=[]
    if raw.startswith("assets/") and ".." not in Path(raw).parts:
        candidates.append(root/raw)
    slug=re.sub(r"[^a-z0-9]+","-",str(job.get("company") or "").lower()).strip("-")
    for ext in ("webp","png","jpg"):
        candidates.append(root/"assets"/"company-approved"/f"{slug}.{ext}")
    for file in candidates:
        if file.is_file():
            try:
                im=Image.open(file)
                im.load()
                return im.convert("RGBA")
            except Exception:
                pass
    return None


def create_header(job:dict,role:str,destination:Path,root:Path)->dict:
    from PIL import Image,ImageDraw
    canvas=Image.new("RGBA",SIZE,(0,0,0,0))
    draw=ImageDraw.Draw(canvas)
    # Compact badge instead of the old large opaque information card.
    draw.rounded_rectangle((132,92,948,383),radius=38,fill=(5,13,31,213),
                           outline=(255,255,255,66),width=3)
    company=str(job.get("company") or "HD Careers")
    logo=_company_logo(job,root)
    if logo:
        logo.thumbnail((570,122),Image.Resampling.LANCZOS)
        # Keep logo readable on dark backgrounds (white backing only behind logo).
        tw,th=logo.size
        patch=Image.new("RGBA",(tw+34,th+18),(255,255,255,244))
        patch.alpha_composite(logo,(17,9))
        canvas.alpha_composite(patch,((SIZE[0]-patch.width)//2,119))
    else:
        draw.text((540,147),company,font=_font(62,True),anchor="mm",fill="#ffffff")
    # Always below the company logo; truncate less important role qualifiers.
    words=role.split()
    lines=[]
    current=""
    f=_font(46,True)
    for word in words:
        candidate=(current+" "+word).strip()
        bbox=draw.textbbox((0,0),candidate,font=f)
        if current and bbox[2]-bbox[0]>740:
            lines.append(current);current=word
        else:current=candidate
    if current:lines.append(current)
    lines=lines[:2] or ["Fresher opportunity"]
    for j,line in enumerate(lines):
        draw.text((540,282+j*57),line,font=f,anchor="mm",fill="#ffffff")
    destination.parent.mkdir(parents=True,exist_ok=True)
    canvas.save(destination)
    return {"companyLogoFound":logo is not None, "roleLines":lines}


def _ass_time(seconds:float)->str:
    c=max(0,int(round(seconds*100)))
    return f"{c//360000}:{(c//6000)%60:02d}:{(c//100)%60:02d}.{c%100:02d}"


def _ass_safe(value:str)->str:
    return str(value).replace("\\","").replace("{","").replace("}","").replace("\n"," ")


def create_ass(words:list[dict],destination:Path,group_size:int=4)->dict:
    if not 2<=group_size<=8:raise ValueError("Unsupported subtitle group size")
    if len(words)<7:raise ValueError("No usable aligned narration")
    for i,w in enumerate(words):
        if w["start"]<0 or w["end"]<=w["start"]:raise ValueError("Invalid word timings")
        if i and w["start"]+0.005<words[i-1]["start"]:raise ValueError("Unordered words")
    header="""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: HDCC,DejaVu Sans,57,&H00FFFFFF,&H00FFFFFF,&HCD000000,&HA0000000,1,0,0,0,100,100,0,0,1,4,1,2,65,65,360,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    dialogue=[]
    for i,word in enumerate(words):
        chunk_start=(i//group_size)*group_size
        group=words[chunk_start:chunk_start+group_size]
        parts=[]
        for j,item in enumerate(group):
            index=chunk_start+j
            color=MAGENTA if index==i else WHITE
            parts.append(r"{\1c"+color+"&}" + _ass_safe(item["text"]))
        text=" ".join(parts)
        start=float(word["start"])
        # Hold the current word until the next word starts; never advance early.
        end=float(words[i+1]["start"]) if i+1<len(words) else float(word["end"])+0.35
        end=max(end,start+0.05)
        dialogue.append(f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},HDCC,,0,0,0,,{text}")
    destination.write_text(header+"\n".join(dialogue)+"\n",encoding="utf-8")
    return {"captionCount":len(dialogue),"lastCaptionSeconds":float(words[-1]["end"])+0.35}


def render(footage:Path,job:dict,role:str,voice:Path,word_file:Path,output:Path,root:Path)->dict:
    if not footage.is_file() or not voice.is_file() or not word_file.is_file():
        raise FileNotFoundError("Approved video footage, narration, and aligned words are all required")
    words=json.loads(word_file.read_text(encoding="utf-8"))
    if not words or float(words[-1]["end"])>13.7:
        raise ValueError("Voiceover too long for a short HD Careers Reel; shorten script first")
    duration=max(10.0,math.ceil((float(words[-1]["end"])+0.85)*10)/10)
    directory=output.parent.resolve()
    directory.mkdir(parents=True,exist_ok=True)
    header=directory/"header-overlay.png"
    captions=directory/"captions.ass"
    logo=create_header(job,role,header,root)
    details=create_ass(words,captions)
    # FFmpeg runs in output directory, making ass=caption.ass path portable.
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-y",
         "-stream_loop","-1","-i",str(footage.resolve()),
         "-loop","1","-i",str(header),
         "-i",str(voice.resolve()),
         "-filter_complex",
         "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
         "crop=1080:1920,fps=30,format=yuv420p[bg];"
         "[1:v]format=rgba[brand];[bg][brand]overlay=0:0:shortest=0,"
         "format=yuv420p,ass=captions.ass[v]",
         "-map","[v]","-map","2:a:0","-t",f"{duration:.2f}",
         "-c:v","libx264","-preset","veryfast","-crf","24",
         "-r","30","-pix_fmt","yuv420p",
         "-c:a","aac","-b:a","160k","-ar","48000",
         "-af","apad","-movflags","+faststart",str(output.resolve())]
    subprocess.run(cmd,check=True,timeout=300,cwd=directory)
    if not output.is_file() or output.stat().st_size<100000:
        raise RuntimeError("Output video missing or invalid")
    return {"durationSeconds":duration, "logo":logo, "captions":details,
            "footage":footage.name,"bytes":output.stat().st_size}
