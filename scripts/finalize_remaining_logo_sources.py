#!/usr/bin/env python3
"""Fill unresolved company logo review entries from identified sources.
Only modifies review files, never production logo mappings.
"""
import json
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from curate_replacement_logo_assets import ROOT,fetch,save_svg,save_raster
p=ROOT/"data/replacement-logo-review.json"
data=json.loads(p.read_text())
urls={
"Reliance Industries":["https://rilstaticasset.akamaized.net/sites/default/files/2023-02/S.1.1_2.png"],
"Aditya Birla Group":[
"https://www.adityabirla.com/_next/static/media/aditya-birla-group-download-logo.a8a380da.webp",
"https://develop.adityabirla.com/_next/static/media/aditya-birla-group-download-logo.a8a380da.webp",
"https://www.adityabirla.com/_next/image/?q=100&url=%2F_next%2Fstatic%2Fmedia%2Faditya-birla-group-download-logo.a8a380da.webp&w=1080"],
"ITC":["https://commons.wikimedia.org/wiki/Special:Redirect/file/ITC_Limited_Logo.svg"],
"Asian Paints":["https://commons.wikimedia.org/wiki/Special:Redirect/file/Asian_Paints_Logo.svg","https://seekvectors.com/files/download/Asian%20Paints.svg"]
}
for name,arr in urls.items():
    if data[name].get("path"): continue
    for url in arr:
        try:
            raw,final,mime=fetch(url,1300000)
            if b"<svg" in raw[:1300]:
                item=save_svg(name,raw,None,final)
            else:
                item=save_raster(name,raw,final)
            data[name].update(item)
            data[name]["status"]="official_brand_asset_review" if name in ("Reliance Industries","Aditya Birla Group") else "review_corporate_brand_asset"
            data[name]["note"]="Identified company-branded asset for visual approval"
            print(name, "SUCCESS", item["path"],flush=True)
            break
        except Exception as exc:
            print(name, "attempt rejected:",str(exc)[:160],flush=True)
# ITC official website may provide a compact corporate logo (avoid third party offerings).
if not data["ITC"].get("path"):
    try:
        url="https://itcportal.com/index.html?lang=en"
        raw,final,_=fetch(url,2500000)
        soup=BeautifulSoup(raw,"html.parser")
        for image in soup.select("img"):
            alt=(image.get("alt") or "").lower()
            src=image.get("src") or image.get("data-src") or ""
            if "logo" not in alt and "itc-logo" not in src.lower():continue
            if not src:continue
            try:
                payload,srcurl,_=fetch(urljoin(final,src))
                data["ITC"].update(save_raster("ITC",payload,srcurl))
                data["ITC"]["status"]="official_brand_asset_review"
                break
            except Exception:continue
    except Exception as exc:print("ITC homepage error",str(exc)[:160],flush=True)
p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
print("AFTER FINAL REVIEW:",sum(bool(v.get("path")) for v in data.values()),"/",len(data),flush=True)
