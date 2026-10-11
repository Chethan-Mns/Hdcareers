#!/usr/bin/env python3
"""Review-only corrections: reject false-positive scraped brand assets.
Replace with correctly identified public corporate SVG sources when available.
"""
import json
from pathlib import Path
from urllib.parse import quote

from curate_replacement_logo_assets import ROOT, OUT, fetch, save_svg, save_raster, slug

manifest=ROOT/"data/replacement-logo-review.json"
rows=json.loads(manifest.read_text())
# Known incorrect imagery from the generic website scraper: corporate subbrands,
# unrelated social-service icons and advertising banners are NOT employer logos.
bad={"Kyndryl","EY","Walmart Global Tech","Reliance Industries","Tata Steel"}
for name in bad:
    row=rows[name]
    row.update(path=None,status="needs_official_asset",source=None,
               note="Rejected unrelated or incorrect page image; awaiting verified corporate mark")
# Verified file names (check Commons image page metadata before editing this list).
commons={
"NTT DATA":"NTT Data 2025.svg",
"Kyndryl":"Kyndryl logo.svg",
"EY":"Ernst & Young logo (2025).svg",
"Walmart Global Tech":"Walmart spark (2025).svg",
"Meesho":"Meesho logo.png",
"Reliance Industries":"Reliance Industries.svg",
"Tata Steel":"Tata Steel Logo.svg",
"Larsen & Toubro":"Larsen-&-Toubro-Logo.svg",
"ITC":"ITC Limited Logo.svg",
"Asian Paints":"Asian Paints Logo.svg",
}
for name,file in commons.items():
    url="https://commons.wikimedia.org/wiki/Special:Redirect/file/"+quote(file)
    try:
        content,resolved,_=fetch(url,1200000)
        if b"<svg" in content[:1600]:
            data=save_svg(name,content,None,resolved)
        else:
            data=save_raster(name,content,resolved)
        rows[name].update(data)
        rows[name]["provenance"]="Wikimedia Commons identified brand mark: "+file
        rows[name]["status"]="review_corporate_brand_asset"
        print(name,":",rows[name]["status"],flush=True)
    except Exception as e:
        rows[name]["note"]="Logo source could not be downloaded: "+str(e)[:110]
        print(name,": NEEDS REVIEW: ",str(e)[:100],flush=True)
# Genpact official source was the real white-on-dark Genpact vector, invisible on
# our white cards. Preserve its geometry; use dark contrast on the preview only.
gen=rows["Genpact"]
if gen.get("path") and gen["path"].endswith(".svg"):
    file=ROOT/gen["path"]
    txt=file.read_text()
    if "fill: #fff" in txt:
        file.write_text(txt.replace("fill: #fff","fill: #1C2853"))
        gen["note"]="Official Genpact vector, color adjusted for contrast in white logo tiles"
        gen["status"]="official_logo_contrast_variant"
# Kill any accidental wrong-brand candidates that could visually mislead.
for name in bad:
    if not rows[name].get("path"):
        rows[name]["status"]="needs_official_asset"
manifest.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\n")
print("REVIEW READY",sum(bool(v.get("path")) for v in rows.values()),"of",len(rows),flush=True)
