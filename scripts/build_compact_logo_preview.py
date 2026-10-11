#!/usr/bin/env python3
"""Download review-only compact company icon candidates. Never mark these as brand-approved."""
import io
import json
import re
import urllib.request
from pathlib import Path
from PIL import Image, ImageChops, ImageStat

ROOT=Path(__file__).resolve().parents[1]
items=json.loads((ROOT/"data/compact-logo-candidates-105.json").read_text())
out=ROOT/"assets/company-marks-preview"
out.mkdir(parents=True,exist_ok=True)
manifest={}
for item in items:
    name,domain=item["name"],item["domain"]
    slug=re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-")
    file=out/(slug+".png")
    try:
        url="https://www.google.com/s2/favicons?domain="+domain+"&sz=256"
        req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; HD-Careers-Logo-Review/1.0)"})
        with urllib.request.urlopen(req,timeout=15) as r:
            raw=r.read(2_000_000)
        img=Image.open(io.BytesIO(raw)).convert("RGBA")
        if min(img.size)<96:
            raise ValueError("source icon below 96px: "+str(img.size))
        # Reject empty/near-monochrome placeholders; human brand review remains mandatory.
        stat=ImageStat.Stat(img.convert("RGB"))
        if sum(stat.stddev)<14:
            raise ValueError("low-detail / likely placeholder")
        background=Image.new("RGBA",img.size,(0,0,0,0))
        bbox=img.getchannel("A").getbbox() or (0,0,*img.size)
        img=img.crop(bbox)
        img.thumbnail((224,224),Image.Resampling.LANCZOS)
        target=Image.new("RGBA",(256,256),(255,255,255,0))
        target.alpha_composite(img,((256-img.width)//2,(256-img.height)//2))
        target.save(file,optimize=True)
        manifest[name]={"status":"candidate_needs_brand_review","path":str(file.relative_to(ROOT)),"domain":domain,"source":url,"size":"256x256"}
    except Exception as exc:
        manifest[name]={"status":"fallback_existing_logo","domain":domain,"reason":str(exc)[:180]}
(ROOT/"data/compact-logo-preview-report.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
print("Downloaded candidates:",sum(x["status"]=="candidate_needs_brand_review" for x in manifest.values()),"of",len(items))
print("Existing fallback:",sum(x["status"]=="fallback_existing_logo" for x in manifest.values()))
