"""Make a legible DataFlair icon from its existing verified employer image.

Runs before validation and site generation. Does not alter original icons.
Only DataFlair receives a cropped asset or an approval mapping.
"""
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/company-icons/dataflair-web-services-pvt-ltd-442f2aa-775d6eb10c.png"
OUTPUT = ROOT / "assets/company-owner/dataflair-compact-v2-20261024.png"
APPROVALS = ROOT / "data/approved-company-logos.json"


def main():
    with Image.open(SOURCE) as original:
        rgba = original.convert("RGBA")
        white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        white.alpha_composite(rgba)
        rgb = white.convert("RGB")

    diff = ImageChops.difference(rgb, Image.new("RGB", rgb.size, "#ffffff")).convert("L")
    bbox = diff.point(lambda c: 255 if c > 24 else 0).getbbox()
    if not bbox:
        raise ValueError("DataFlair asset is empty")
    cropped = rgb.crop(bbox)
    # Enlarge the real branded artwork, not the whitespace around it.
    art = ImageOps.contain(cropped, (352, 352), Image.Resampling.LANCZOS)
    result = Image.new("RGB", (384, 384), "white")
    result.paste(art, ((384 - art.width) // 2, (384 - art.height) // 2))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result.save(OUTPUT, "PNG", optimize=True)
    approvals = json.loads(APPROVALS.read_text(encoding="utf-8"))
    target = OUTPUT.relative_to(ROOT).as_posix()
    if approvals.get("DataFlair Web Services Pvt Ltd") != target:
        approvals["DataFlair Web Services Pvt Ltd"] = target
        APPROVALS.write_text(json.dumps(approvals, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"DataFlair icon ready: original {rgb.size}, visible region {bbox}, output 384x384: {target}")


if __name__ == "__main__":
    main()
