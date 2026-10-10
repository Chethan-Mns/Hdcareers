#!/usr/bin/env python3
"""Shadow-only fifteen-second cinematic hiring Reel, no social publishing."""
import argparse
import json
import math
import random
import shutil
import subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageFilter

ROOT=Path(__file__).resolve().parents[2]
W,H=540,960
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REG="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
def ft(n,bold=True):return ImageFont.truetype(FONT if bold else REG,n)
def run(cmd):subprocess.run(cmd,check=True)
def city(path):
    rng=random.Random(12)
    im=Image.new("RGB",(600,1066))
    pixels=im.load()
    for y in range(1066):
        for x in range(600):
            g=max(0,1-math.hypot((x-400)/450,(y-250)/500))
            pixels[x,y]=(int(6+15*g),int(17+31*g),int(35+44*g))
    d=ImageDraw.Draw(im)
    for _ in range(25):
        x,y=rng.randrange(600),rng.randrange(720);radius=rng.randrange(10,44)
        d.ellipse((x-radius,y-radius,x+radius,y+radius),fill=(18,48,76))
    im=im.filter(ImageFilter.GaussianBlur(18));d=ImageDraw.Draw(im)
    for x in range(-25,640,39):
        top=rng.randint(235,640);bw=rng.randint(24,55)
        d.rectangle((x,top,x+bw,1066),fill=(7+rng.randrange(12),14+rng.randrange(18),30+rng.randrange(18)))
        d.line((x,top,x+bw,top),fill=(45,130,168),width=2)
        for y in range(top+15,1060,22):
            for wx in range(x+5,x+bw-4,11):
                if rng.random()<0.52:
                    d.rectangle((wx,y,wx+4,y+6),fill=rng.choice([(238,162,75),(55,165,202),(151,190,210)]))
    im.save(path)
def plate(path,scene,name,logo_path=None):
    im=Image.new("RGBA",(W,H),(0,0,0,0));d=ImageDraw.Draw(im)
    for y in range(H):
        opacity=int(85+min(120,max(0,(y-340)*.3)))
        d.line((0,y,W,y),fill=(3,10,23,opacity))
    d.rounded_rectangle((34,68,506,134),radius=17,fill=(7,21,45,232),outline=(78,179,210,150),width=2)
    d.text((58,88),"HD  /  CAREERS",font=ft(20),fill="white")
    d.rounded_rectangle((34,158,506,214),radius=12,fill=(12,42,62,225))
    d.text((58,176),"FRESHER HIRING  •  VERIFIED JOB",font=ft(16),fill=(137,237,231))
    d.rounded_rectangle((34,305,506,754),radius=27,fill=(3,11,26,226),outline=(67,143,183,155),width=2)
    d.rectangle((62,338,70,389),fill=(48,217,207))
    d.text((93,340),name.upper(),font=ft(33),fill="white")
    if logo_path and Path(logo_path).is_file():
        try:
            logo=Image.open(logo_path).convert("RGBA")
            logo.thumbnail((53,53))
            d.rounded_rectangle((417,334,487,404),radius=12,fill=(255,255,255,241))
            im.alpha_composite(logo,(452-logo.width//2,369-logo.height//2))
        except OSError:pass
    titles=["IS HIRING!","BENGALURU","WANT TO APPLY?"]
    details=[["AI / ML COMPUTATIONAL","SCIENCE ASSOCIATE"],["BE / BTECH","GRADUATES"],["COMMENT","LINK"]]
    badges=["FRESHERS • 0–1 YEAR","0–1 YEAR EXPERIENCE","JOB DETAILS IN YOUR DMs"]
    captions=[["Hey guys! Accenture is hiring freshers","for an AI and ML Associate role."],["The job is in Bengaluru. BE or BTech","graduates with 0–1 year can apply."],["Interested? Comment LINK below","for the application details!"]]
    d.text((63,415),titles[scene],font=ft(35),fill=(255,205,105))
    for i,line in enumerate(details[scene]):d.text((63,488+i*51),line,font=ft(28),fill="white")
    d.rounded_rectangle((62,650,475,713),radius=16,fill=(18,76,89,238))
    d.text((83,669),badges[scene],font=ft(18),fill=(201,250,243))
    d.rounded_rectangle((30,810,510,904),radius=24,fill=(7,20,37,228))
    for i,line in enumerate(captions[scene]):d.text((54,829+i*27),line,font=ft(17,False),fill="white")
    d.text((37,920),"PREVIEW ONLY  •  HDCAREERS.IN",font=ft(13),fill=(141,169,183))
    im.save(path)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--jobs",default=str(ROOT/"data/jobs.json"))
    p.add_argument("--job-id",type=int,default=112)
    p.add_argument("--output",default=str(ROOT/"reel-shadow/output"))
    p.add_argument("--background",default="")
    a=p.parse_args()
    jobs=json.loads(Path(a.jobs).read_text(encoding="utf-8"))
    j=next((x for x in jobs if x.get("id")==a.job_id),None)
    if not j or j.get("status")!="active" or not j.get("page") or not j.get("apply"):
        raise SystemExit("No verified published active job")
    if a.job_id!=112 or j.get("company")!="Accenture" or "S01665344" not in j["apply"]:
        raise SystemExit("This demo is locked to verified Accenture AIOC-S01665344")
    if not shutil.which("ffmpeg") or not shutil.which("espeak"):raise SystemExit("Install ffmpeg and espeak")
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    work=out/"work";work.mkdir(exist_ok=True);base=f"reel-{a.job_id}"
    city(work/"city.png")
    logo=ROOT/str(j.get("logoPath","")) if j.get("logoPath") else None
    for i in range(3):plate(work/f"panel{i}.png",i,j["company"],logo)
    script="Hey guys! Accenture is hiring freshers for an AI and ML Associate role. The job is in Bengaluru. B E or B Tech graduates with zero to one year experience can apply. Interested? Comment link below for the application details!"
    (out/f"{base}-script.txt").write_text(script+"\n",encoding="utf-8")
    captions=["Hey guys! Accenture is hiring freshers\nfor an AI and ML Associate role.","The job is in Bengaluru. BE or BTech\ngraduates with 0–1 year can apply.","Interested? Comment LINK below\nfor the application details!"]
    def stamp(sec):return f"00:00:{sec:02d},000"
    (out/f"{base}.srt").write_text("\n\n".join(f"{i+1}\n{stamp(i*5)} --> {stamp((i+1)*5)}\n{caption}" for i,caption in enumerate(captions))+"\n",encoding="utf-8")
    destination="https://hdcareers.in/"+j["page"].lstrip("/")
    licensed=bool(a.background and Path(a.background).is_file())
    credit=("\nBackground adapted from 'City skyline (time lapse)' by YouTube user Editor, CC BY 3.0. https://commons.wikimedia.org/wiki/File:City_skyline_(time_lapse).webm https://creativecommons.org/licenses/by/3.0/" if licensed else "")
    (out/f"{base}-caption.txt").write_text(f"🚨 Accenture is hiring freshers!\n\nRole: AI/ML Computational Science Associate\n📍 Bengaluru\n🎓 BE / BTech | 0–1 year\n\n💬 Comment LINK for the job details.\n🔗 {destination}\n\n#Accenture #FresherJobs #BTechJobs #BengaluruJobs #HDCareers"+credit+"\n",encoding="utf-8")
    run(["espeak","-v","en-us","-s","196","-a","185","-w",str(work/"voice.wav"),script])
    duration=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(work/"voice.wav")]).decode().strip())
    if duration>15:raise SystemExit(f"Narration exceeds fifteen seconds: {duration:.2f}s")
    bg=["-stream_loop","-1","-i",a.background] if licensed else ["-loop","1","-framerate","24","-i",str(work/"city.png")]
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-y"]+bg+["-i",str(work/"voice.wav")]
    for i in range(3):cmd+=["-loop","1","-framerate","24","-i",str(work/f"panel{i}.png")]
    graph=("[0:v]scale=600:1066:force_original_aspect_ratio=increase,crop=540:960:"
        "x='(iw-ow)/2+15*sin(n/35)':y='(ih-oh)/2+10*cos(n/40)',"
        "eq=brightness=-0.055:saturation=0.86,setsar=1[bg];"
        "[bg][2:v]overlay=0:0:enable='between(t,0,4.999)'[a];"
        "[a][3:v]overlay=0:0:enable='between(t,5,9.999)'[b];"
        "[b][4:v]overlay=0:0:enable='gte(t,10)',scale=1080:1920:flags=bicubic,fps=24,format=yuv420p[v]")
    cmd+=["-filter_complex",graph,"-map","[v]","-map","1:a:0","-af","apad=pad_dur=15,atrim=duration=15","-t","15","-c:v","libx264","-preset","ultrafast","-crf","23","-c:a","aac","-b:a","128k","-movflags","+faststart",str(out/f"{base}.mp4")]
    run(cmd)
    run(["ffmpeg","-hide_banner","-loglevel","error","-y","-ss","2","-i",str(out/f"{base}.mp4"),"-frames:v","1",str(out/f"{base}-cover.jpg")])
    manifest={"jobId":a.job_id,"company":j["company"],"role":j["role"],"jobUrl":destination,"officialApplyUrl":j["apply"],"status":"shadow-only","seconds":15,"video":f"{base}.mp4","cover":f"{base}-cover.jpg","caption":f"{base}-caption.txt","script":f"{base}-script.txt","subtitles":f"{base}.srt","voice":"espeak placeholder TTS","background":"licensed city footage, attribution in caption" if licensed else "original cinematic moving illustration fallback"}
    (out/f"{base}.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps({"ok":True,"durationSeconds":15,"narrationSeconds":duration,"output":str(out/f"{base}.mp4")}))
if __name__=="__main__":main()
