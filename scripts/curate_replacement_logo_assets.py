#!/usr/bin/env python3
"""Preview-only downloader for requested HD Careers compact company marks.
Never modify published company logo mappings until the owner approves the gallery.
"""
import io
import json
import re
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from pathlib import Path
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup
from PIL import Image, ImageOps, ImageStat

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets/company-marks-review"
OUT.mkdir(parents=True,exist_ok=True)
MANIFEST = ROOT / "data/replacement-logo-review.json"
FAVICON = json.loads((ROOT/"data/compact-logo-preview-report.json").read_text())
REPLACEMENTS = [
"TCS","IBM","NTT DATA","Persistent Systems","Hexaware","EPAM Systems","Brillio",
"Zensar Technologies","Kyndryl","Genpact","EY","Oracle","SAP","Salesforce","Cisco",
"Intel","Autodesk","Walmart Global Tech","Paytm","Meesho","American Express","Visa",
"Bosch","GE Vernova","L&T Technology Services","Reliance Industries","Tata Motors",
"Tata Steel","Larsen & Toubro","Aditya Birla Group","ITC","Nestlé","Asian Paints",
"IndiGo","DHL","Amazon Operations"]
# Brand icon references (SVG, not a generic favicon), sourced from public logo collections.
# These are review candidates only, with provenance retained in the manifest.
SI = "https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/"
GL = "https://raw.githubusercontent.com/gilbarbara/logos/master/logos/"
VECTORS = {
"TCS":(SI+"tcs.svg","#0068B5"),
"IBM":(GL+"ibm.svg",None),
"Persistent Systems":(SI+"persistent.svg","#E62429"),
"Zensar Technologies":(SI+"zensar.svg","#1E4E8C"),
"Oracle":(GL+"oracle.svg",None),
"SAP":(SI+"sap.svg","#0A6ED1"),
"Salesforce":(GL+"salesforce.svg",None),
"Cisco":(SI+"cisco.svg","#049FD9"),
"Intel":(SI+"intel.svg","#0068B5"),
"Autodesk":(SI+"autodesk.svg","#0B0B0B"),
"Paytm":(SI+"paytm.svg","#002970"),
"American Express":(SI+"americanexpress.svg","#016FD0"),
"Visa":(SI+"visa.svg","#1A1F71"),
"Bosch":(SI+"bosch.svg","#E20015"),
"IndiGo":(SI+"indigo.svg","#073A87"),
"DHL":(SI+"dhl.svg","#D40511"),
}
def slug(name): return re.sub("[^a-z0-9]+","-",name.casefold()).strip("-")
def fetch(url,limit=1200000):
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; HD-Careers-Logo-Review/1.0)",
                             "Accept":"image/avif,image/webp,image/svg+xml,image/png,image/*;q=0.9,*/*;q=0.8"})
    with urlopen(req,timeout=12) as r:
        if int(r.headers.get("Content-Length") or 0)>limit: raise ValueError("oversized")
        body=r.read(limit+1)
        if len(body)>limit: raise ValueError("oversized")
        return body,r.url,r.headers.get("Content-Type","")
def sanitize_svg(raw,color=None):
    s=raw.decode("utf-8-sig",errors="replace").strip()
    s=re.sub(r"<\?xml[^>]*\?>","",s)
    s=re.sub(r"<!DOCTYPE[^>]*>","",s)
    if not re.search(r"<svg\b",s): raise ValueError("not svg")
    if len(s)>150000: raise ValueError("svg too large")
    if re.search(r"<script|<foreignObject|onload\s*=|onerror\s*=|<iframe|javascript:|<image\b|<use\b|url\(\s*https?://",s,re.I):
        raise ValueError("svg has dynamic content or external resource")
    if color and "fill=" not in s[:s.find(">")+1]:
        s=s.replace("<svg ","<svg fill=\""+color+"\" ",1)
    ET.fromstring(s)
    return s
def save_svg(name,raw,color,source):
    svg=sanitize_svg(raw,color)
    dest=OUT/(slug(name)+".svg")
    dest.write_text(svg)
    return {"status":"vector_candidate","path":str(dest.relative_to(ROOT)),"source":source,"format":"svg"}
def save_raster(name,raw,source):
    im=Image.open(io.BytesIO(raw)).convert("RGBA")
    w,h=im.size
    if min(w,h)<110 or max(w,h)<150: raise ValueError("raster source too small")
    if max(w,h)/min(w,h)>6: raise ValueError("very elongated wordmark")
    im.thumbnail((460,460),Image.Resampling.LANCZOS)
    a=im.getchannel("A"); box=a.getbbox()
    if box: im=im.crop(box)
    im.thumbnail((440,440),Image.Resampling.LANCZOS)
    canvas=Image.new("RGBA",(512,512),(255,255,255,0))
    canvas.alpha_composite(im,((512-im.width)//2,(512-im.height)//2))
    dest=OUT/(slug(name)+".png")
    canvas.save(dest,optimize=True)
    return {"status":"official_raster_candidate","path":str(dest.relative_to(ROOT)),"source":source,"format":"png","sourceSize":[w,h]}
def official(name,domain):
    homepage="https://www."+domain+"/"
    try:
        html,final_url,_=fetch(homepage,2500000)
    except Exception:
        html,final_url,_=fetch("https://"+domain+"/",2500000)
    soup=BeautifulSoup(html,"html.parser")
    variants=[]
    # Strongest evidence: company-provided brand imagery used in a logo/header component.
    for t in soup.select("img,source"):
        url=t.get("src") or t.get("data-src") or t.get("srcset","").split(",")[0].split(" ")[0]
        if not url or str(url).startswith("data:"): continue
        url=urljoin(final_url,url)
        meta=" ".join(filter(None,[t.get("alt",""),t.get("id","")," ".join(t.get("class",[])),url.split("/")[-1]])).lower()
        if not any(k in meta for k in ("logo","brand")):continue
        if any(x in meta for x in ("partner","customer","client","footer-social","linkedin","facebook","twitter","meta","adobe")):continue
        score=10 if "logo" in (t.get("alt") or "").lower() else 2
        if "header" in meta or "navbar" in meta or "site-logo" in meta: score+=5
        if name.casefold().split()[0] in meta: score+=2
        if ".svg" in url.lower().split("?")[0]:score+=5
        variants.append((score,url))
    for t in soup.select("link[rel=apple-touch-icon],link[rel=icon]"):
        url=t.get("href")
        if url:variants.append((1,urljoin(final_url,url)))
    seen=set()
    for _,url in sorted(variants,reverse=True):
        if url in seen:continue
        seen.add(url)
        try:
            raw,real,content_type=fetch(url)
            if "<svg" in raw[:1500].decode("utf8",errors="ignore"):
                return save_svg(name,raw,None,real)
            if "image" in content_type.lower() or raw[:4] in (b"\x89PNG",b"RIFF"):
                return save_raster(name,raw,real)
        except Exception: continue
    raise ValueError("No suitable official logo file detected")
if __name__ == '__main__':
    results={}
    for name in REPLACEMENTS:
        domain=FAVICON[name]["domain"]
        record={"name":name,"domain":domain}
        try:
            if name=="Amazon Operations":
                file=ROOT/"assets/logos/amazon-mark.svg"
                record.update(save_svg(name,file.read_bytes(),None,"repository:assets/logos/amazon-mark.svg"))
                record["status"]="existing_compact_mark_candidate"
            elif name in VECTORS:
                url,color=VECTORS[name]
                try:
                    raw,final,_=fetch(url)
                    record.update(save_svg(name,raw,color,final))
                except Exception as exc:
                    record.update(official(name,domain))
                    record["fallbackReason"]=str(exc)[:180]
            else:
                record.update(official(name,domain))
        except Exception as exc:
            prev=FAVICON[name]
            if prev["status"]=="candidate_needs_brand_review" and (ROOT/prev["path"]).is_file():
                record.update(status="existing_local_candidate",path=prev["path"],source="existing 256px cached icon",note="Official compact mark still needs verification")
            else:
                record.update(status="needs_official_asset",path=None,note=str(exc)[:170])
        results[name]=record
        print(f"{name}: {record['status']} {record.get('path')}",flush=True)
    MANIFEST.write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n")
    print("READY",sum(bool(x.get("path")) for x in results.values()),"of",len(results),flush=True)
    