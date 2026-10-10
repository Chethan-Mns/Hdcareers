#!/usr/bin/env python3
"""Shadow Reel V2: original edit with licensed generic office footage and neural voice."""
from __future__ import annotations
import asyncio
import json
import math
import random
import re
import shutil
import subprocess
import urllib.request
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"reel-shadow"/"v2"
CLIPS=OUT/"stock"
W,H=720,1280
JOB_ID=112
SCRIPT="Hey guys! Accenture is hiring freshers for an AI and M L Associate role. The job is in Bengaluru. B E or B Tech graduates with zero to one year of experience can apply. Interested? Comment LINK below for the application!"
SOURCES=[
    ("7652293","25","Colleagues walking in modern office lobby","Kindel Media"),
    ("8347239","25","Modern office desks and computers","Kampus Production"),
    ("12894330","24","People working at desks","Mizuno K"),
    ("5981604","25","Office reception meeting","cottonbro studio"),
    ("8347238","25","Modern office interior","Kampus Production"),
]
CREDIT="B-roll is illustrative and does not depict Accenture offices. Stock footage: Pexels / Kindel Media, Kampus Production, Mizuno K, cottonbro studio, https://www.pexels.com/license/"
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
def run(args):
    print("+", " ".join(str(x) for x in args[:12]),flush=True)
    subprocess.run(args,check=True)

def valid_video(path):
    if not path.exists() or path.stat().st_size<100_000:return False
    try:
        s=subprocess.check_output(["ffprobe","-v","error","-show_entries","stream=width,height","-of","default=nw=1",str(path)],timeout=10)
        return b"width=" in s
    except Exception:return False

def fetch_clips():
    CLIPS.mkdir(parents=True,exist_ok=True)
    good=[]
    for key,fps,title,artist in SOURCES:
        target=CLIPS/f"{key}.mp4"
        if valid_video(target):
            good.append((target,title,artist))
            if len(good)>=4:break
            continue
        attempts=[f"{key}-hd_720_1280_{fps}fps.mp4",f"{key}-hd_1080_1920_{fps}fps.mp4",f"{key}-uhd_2160_3840_{fps}fps.mp4"]
        for file in attempts:
            url=f"https://videos.pexels.com/video-files/{key}/{file}"
            try:
                req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
                with urllib.request.urlopen(req,timeout=18) as response,open(target,"wb") as f:
                    limit=80*1024*1024
                    while True:
                        part=response.read(1024*1024)
                        if not part:break
                        f.write(part)
                        if f.tell()>limit:raise RuntimeError("Source file too large")
                if valid_video(target):
                    good.append((target,title,artist))
                    print("Using",key,file,target.stat().st_size,flush=True)
                    break
            except Exception as e:
                print("Footage candidate skipped",file,str(e)[:90],flush=True)
                target.unlink(missing_ok=True)
        if len(good)>=4:break
    if not good:raise RuntimeError("No licensed stock video is available. Refusing to reuse the uploaded reference Reel.")
    return good

async def synthesize():
    import edge_tts
    voice=OUT/"voice.mp3"
    if voice.exists() and voice.stat().st_size>10000:
        return voice,[]
    boundaries=[]
    comm=edge_tts.Communicate(SCRIPT,voice="en-IN-PrabhatNeural",rate="+20%",pitch="+1Hz")
    with voice.open("wb") as f:
        async for chunk in comm.stream():
            if chunk["type"]=="audio":f.write(chunk["data"])
            if chunk["type"]=="WordBoundary":
                boundaries.append({"text":chunk["text"],"start":chunk["offset"]/10**7,"duration":chunk["duration"]/10**7})
    if voice.stat().st_size<10000:raise RuntimeError("Neural narration returned empty audio.")
    return voice,boundaries

def art():
    p=OUT/"title.png"
    base=Image.new("RGBA",(W,H),(0,0,0,0))
    d=ImageDraw.Draw(base)
    # Readable title + subtle gradients, while footage stays visible.
    for y in range(0,445):
        alpha=round(180*(1-y/445)**1.45)
        d.line((0,y,W,y),fill=(4,9,18,alpha))
    for y in range(760,H):
        alpha=round(17+(y-760)/(H-760)*137)
        d.line((0,y,W,y),fill=(3,5,13,alpha))
    bold=lambda n:ImageFont.truetype(FONT,n)
    d.text((52,92),"ACCENTURE",font=bold(63),fill=(255,255,255,255),stroke_width=2,stroke_fill=(0,0,0,128))
    d.rounded_rectangle((51,190,475,253),radius=16,fill=(20,248,151,230))
    d.text((72,203),"FRESHER HIRING",font=bold(31),fill=(0,43,39,255))
    d.text((54,279),"AI/ML ASSOCIATE",font=bold(36),fill=(255,255,255,255),stroke_width=2,stroke_fill=(0,0,0,120))
    d.rounded_rectangle((52,348,570,397),radius=12,fill=(0,0,0,155))
    d.text((72,358),"BENGALURU  ·  0–1 YEAR",font=bold(24),fill=(251,255,255,255))
    d.text((52,1214),"ILLUSTRATIVE OFFICE FOOTAGE",font=bold(14),fill=(235,243,252,177))
    base.save(p)
    return p

def ass_time(t):
    t=max(0.,t)
    return f"{int(t//3600)}:{int(t//60)%60:02}:{int(t%60):02}.{int(t*100)%100:02}"

def escapes(s):
    return s.replace("\\","").replace("{","").replace("}","").replace("\n"," ")

def subtitles(boundaries,duration):
    dest=OUT/"captions.ass"
    # Segmented karaoke captions: each narrated word briefly turns magenta.
    if not boundaries:
        words=SCRIPT.split()
        boundaries=[{"text":w,"start":i*duration/len(words),"duration":duration/len(words)} for i,w in enumerate(words)]
    words=[(str(e["text"]).strip(),float(e["start"])) for e in boundaries if str(e["text"]).strip()]
    lines=[
        "[Script Info]","ScriptType: v4.00+","PlayResX: 720","PlayResY: 1280","WrapStyle: 0","ScaledBorderAndShadow: yes",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Words,DejaVu Sans,31,&H00FFFFFF,&H00FFFFFF,&H00040C13,&H80000000,1,0,0,0,100,100,0,0,1,3,1,2,35,35,340,1",
        "Style: CTA,DejaVu Sans,34,&H0000FFBF,&H0000FFBF,&H0005140F,&H80000000,1,0,0,0,100,100,0,0,1,3,1,2,35,35,160,1",
        "[Events]","Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]
    # Group 4 to 7 words, keeping each dynamic phrase inside a reasonable width.
    groups=[];at=0
    while at<len(words):
        end=min(at+6,len(words))
        while end>at+3 and sum(len(x[0]) for x in words[at:end])+end-at>42:end-=1
        groups.append((at,end));at=end
    for start,end in groups:
        for i in range(start,end):
            current=words[i][1]
            next_start=words[i+1][1] if i+1<len(words) else duration
            if next_start<=current:next_start=current+.13
            bits=[]
            for j in range(start,end):
                w=escapes(words[j][0])
                if i==j:bits.append(r"{\c&H00E560F5&}"+w+r"{\c&H00FFFFFF&}")
                else:bits.append(w)
            text=" ".join(bits)
            lines.append(f"Dialogue: 0,{ass_time(current)},{ass_time(min(duration,next_start))},Words,,0,0,0,,{text}")
    lines.append(f"Dialogue: 1,{ass_time(12.1)},{ass_time(14.85)},CTA,,0,0,0,,COMMENT LINK ↓")
    dest.write_text("\n".join(lines)+"\n",encoding="utf-8")
    return dest

def voice_duration(path):
    return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)]).decode())

def synth_music():
    import numpy as np
    sample=24000;n=int(15*sample)
    t=np.arange(n,dtype=np.float32)/sample
    audio=np.zeros(n,dtype=np.float32)
    chords=[(164.81,196,261.63),(146.83,174.61,261.63),(174.61,220,293.66),(130.81,196,261.63)]
    for i,chord in enumerate(chords):
        a=i*3.75;b=min(15.,a+3.8);s=int(a*sample);e=int(b*sample);ts=t[s:e]-a
        env=np.minimum(1,ts/.5)*np.minimum(1,(b-a-ts)/.65)
        layer=sum((np.sin(2*np.pi*freq*ts)+.2*np.sin(4*np.pi*freq*ts))/len(chord) for freq in chord)
        audio[s:e]+=(layer*env*.095)
    bpm=111;beat=60/bpm
    rng=np.random.default_rng(18)
    for onset in np.arange(0,15,beat):
        s=int(onset*sample);end=min(n,s+int(.15*sample));tt=np.arange(end-s)/sample
        if len(tt):audio[s:end]+=np.sin(2*np.pi*(85-45*tt/.15)*tt)*np.exp(-tt*32)*.17
    for onset in np.arange(beat/2,15,beat):
        s=int(onset*sample);end=min(n,s+int(.05*sample));tt=np.arange(end-s)/sample
        if len(tt):audio[s:end]+=rng.normal(0,.02,len(tt))*np.exp(-tt*58)
    audio=np.clip(audio,-.75,.75)
    with wave.open(str(OUT/"bed.wav"),"wb") as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(sample)
        f.writeframes((audio*32767).astype("<i2").tobytes())
    return OUT/"bed.wav"

def render(clips,voice,marks):
    title=art();sound=synth_music();duration=voice_duration(voice)
    print("Narration duration",duration,flush=True)
    if duration>15.1:raise RuntimeError(f"Voiceover too long ({duration:.2f}s). Shorten the script.")
    sub=subtitles(marks,min(duration,15))
    segdur=[3.3,3.6,3.5,4.6]
    pieces=[]
    for i,duration in enumerate(segdur):
        src=clips[i%len(clips)][0]
        seg=OUT/f"shot-{i}.mp4"
        run(["ffmpeg","-hide_banner","-loglevel","error","-y","-stream_loop","-1","-ss",str(i*.63),"-i",str(src),"-t",str(duration),"-vf",
             "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1,fps=30,eq=brightness=-0.035:saturation=0.93,format=yuv420p",
             "-c:v","libx264","-preset","veryfast","-crf","24","-an",str(seg)])
        pieces.append(seg)
    concat=OUT/"shots.txt";concat.write_text("".join("file '"+p.name+"'\n" for p in pieces))
    run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(OUT/"shots.mp4")])
    ffilter=f"[0:v][1:v]overlay=0:0:format=auto,ass={sub.as_posix()},scale=1080:1920:flags=lanczos,format=yuv420p[v];[2:a]volume=1.12[voice];[3:a]volume=0.27[bed];[voice][bed]amix=inputs=2:duration=longest:dropout_transition=0,apad=pad_dur=15,atrim=duration=15[a]"
    output=OUT/"HD_Careers_Accenture_Reel_V2.mp4"
    run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(OUT/"shots.mp4"),"-loop","1","-framerate","30","-i",str(title),"-i",str(voice),"-i",str(sound),"-filter_complex",ffilter,"-map","[v]","-map","[a]","-t","15","-r","30","-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-b:a","160k","-movflags","+faststart",str(output)])
    run(["ffmpeg","-hide_banner","-loglevel","error","-y","-ss","1.8","-i",str(output),"-frames:v","1",str(OUT/"HD_Careers_Accenture_V2_Cover.jpg")])
    url="https://hdcareers.in/jobs/accenture-ai-ml-computational-science-associate-bengaluru-aioc-s01665344.html"
    caption="🚨 ACCENTURE IS HIRING FRESHERS!\n\n💼 AI/ML Computational Science Associate\n📍 Bengaluru\n🎓 BE/BTech | 0–1 year experience\n💬 Comment LINK for the application details.\n\n🔗 "+url+"\n\n#Accenture #FresherJobs #BTechJobs #BengaluruJobs #HDCareers\n\n"+CREDIT+"\n"
    (OUT/"HD_Careers_Accenture_V2_Caption.txt").write_text(caption)
    (OUT/"HD_Careers_Accenture_V2_Script.txt").write_text(SCRIPT+"\n")
    manifest={"jobId":112,"company":"Accenture","seconds":15,"status":"shadow-only","output":output.name,"caption":"HD_Careers_Accenture_V2_Caption.txt","sourceVideos":[{"url":f"https://www.pexels.com/video/{file.stem}/","title":name,"by":artist} for file,name,artist in clips],"neuralVoice":"en-IN-PrabhatNeural","record":"Accenture AIOC-S01665344, verified published 10 Oct 2026","srt":"captions.ass"}
    (OUT/"v2-manifest.json").write_text(json.dumps(manifest,indent=2))
    print("SUCCESS:",output,output.stat().st_size,flush=True)

if __name__=="__main__":
    OUT.mkdir(parents=True,exist_ok=True)
    clips=fetch_clips()
    voice,marks=asyncio.run(synthesize())
    render(clips,voice,marks)
