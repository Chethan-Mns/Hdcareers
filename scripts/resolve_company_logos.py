from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
import hashlib
from io import BytesIO
import ipaddress
import json
from pathlib import Path
import re
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlparse
from urllib.request import Request, build_opener

from PIL import Image, ImageChops, ImageOps

ROOT = Path(__file__).resolve().parents[1]
JOBS_PATH = ROOT / "data" / "jobs.json"
DOMAIN_PATH = ROOT / "data" / "company-logo-domains.json"
DIRECT_PATH = ROOT / "data" / "company-logo-direct.json"
QUALITY_FALLBACK_PATH = ROOT / "data" / "company-logo-quality-fallbacks.json"
MANIFEST_PATH = ROOT / "data" / "company-logos.json"
ASSET_DIR = ROOT / "assets" / "company-icons"

GENERIC_HOSTS = (
    "myworkdayjobs.com", "myworkdaysite.com", "greenhouse.io", "lever.co",
    "successfactors.com", "taleo.net", "oraclecloud.com", "icims.com",
    "smartrecruiters.com", "workable.com", "infosysapps.com",
)

USER_AGENT = "HD-Careers-Official-Logo-Resolver/2.0"
MAX_HTML = 1_500_000
MAX_ICON = 1_500_000
MIN_RASTER_SIDE = 96
GOOD_RASTER_SIDE = 160
OUTPUT_SIZE = 384


class IconParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.icons: list[tuple[int, str, str]] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "link":
            return
        data = {str(k).lower(): str(v or "") for k, v in attrs}
        rel = data.get("rel", "").lower()
        href = data.get("href", "").strip()
        if not href or "icon" not in rel:
            return

        sizes = data.get("sizes", "")
        href_path = urlparse(href).path.lower()
        score = 180

        if href_path.endswith(".svg") or "svg" in data.get("type", "").lower():
            score = 390
        elif "apple-touch-icon" in rel:
            score = 320
        elif "mask-icon" in rel:
            score = 360
        elif "shortcut icon" in rel:
            score = 190
        elif rel.strip() == "icon":
            score = 220

        match = re.search(r"(\d+)x(\d+)", sizes)
        if match:
            score += min(int(match.group(1)), int(match.group(2)), 512) // 2

        self.icons.append((score, href, rel))


def host_of(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlparse(raw if "://" in raw else "https://" + raw)
        return (parsed.hostname or "").lower().removeprefix("www.")
    except Exception:
        return ""


def is_generic(host: str) -> bool:
    clean = host_of(host)
    return any(clean == item or clean.endswith("." + item) for item in GENERIC_HOSTS)


def public_https(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            return False
        addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
        return bool(addresses) and all(ipaddress.ip_address(row[4][0]).is_global for row in addresses)
    except Exception:
        return False


def official_domain(job: dict, overrides: dict[str, str]) -> str:
    company = str(job.get("company", "")).strip()
    direct = host_of(overrides.get(company, ""))
    if direct:
        return direct

    for field in ("companyWebsite", "careersUrl", "domain", "apply"):
        host = host_of(job.get(field, ""))
        if host and not is_generic(host):
            for prefix in ("careers.", "jobs.", "careersglobal.", "globalcareers."):
                if host.startswith(prefix) and host.count(".") >= 2:
                    host = host[len(prefix):]
                    break
            return host
    return ""


def fetch(url: str, limit: int) -> tuple[bytes, str, str]:
    if not public_https(url):
        raise ValueError("non-public or non-HTTPS URL")
    req = Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,image/svg+xml,image/avif,image/webp,image/png,image/jpeg,image/x-icon,*/*;q=0.7",
    })
    with build_opener().open(req, timeout=7) as res:
        body = res.read(limit + 1)
        if len(body) > limit:
            raise ValueError("response too large")
        return body, str(res.headers.get("Content-Type", "")).lower(), res.geturl()


def sniff_ext(body: bytes, content_type: str, url: str) -> str:
    start = body.lstrip()[:300].lower()
    if start.startswith(b"<svg") or b"<svg" in start or "image/svg+xml" in content_type:
        return ".svg"
    if body.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if body.startswith(b"\x00\x00\x01\x00"):
        return ".ico"
    if body.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if body[:4] == b"RIFF" and body[8:12] == b"WEBP":
        return ".webp"
    if "image/png" in content_type:
        return ".png"
    if "image/x-icon" in content_type or "image/vnd.microsoft.icon" in content_type:
        return ".ico"
    if "image/jpeg" in content_type:
        return ".jpg"
    if "image/webp" in content_type:
        return ".webp"
    suffix = Path(urlparse(url).path).suffix.lower()
    return suffix if suffix in {".svg", ".png", ".ico", ".jpg", ".jpeg", ".webp"} else ""


def slugify(company: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", company.lower()).strip("-")[:70] or "company"
    digest = hashlib.sha1(company.encode("utf-8")).hexdigest()[:7]
    return f"{base}-{digest}"


def candidate_urls(domain: str, direct_url: str = "") -> list[tuple[int, str, str]]:
    base = f"https://{domain}/"
    candidates: list[tuple[int, str, str]] = []

    if direct_url:
        candidates.append((700, direct_url, "official high-resolution logo override"))

    try:
        html_body, content_type, final_url = fetch(base, MAX_HTML)
        if "text/html" in content_type or html_body.lstrip().startswith((b"<!DOCTYPE", b"<html", b"<HTML")):
            parser = IconParser()
            parser.feed(html_body.decode("utf-8", errors="replace"))
            for score, href, rel in parser.icons:
                candidates.append((score, urljoin(final_url, href), rel))
    except Exception:
        pass

    defaults = [
        (380, urljoin(base, "/favicon.svg"), "favicon SVG default"),
        (340, urljoin(base, "/apple-touch-icon.png"), "apple-touch-icon default"),
        (315, urljoin(base, "/favicon-512x512.png"), "favicon 512 default"),
        (300, urljoin(base, "/favicon-192x192.png"), "favicon 192 default"),
        (260, urljoin(base, "/favicon-180x180.png"), "favicon 180 default"),
        (210, urljoin(base, "/favicon-96x96.png"), "favicon 96 default"),
        (120, urljoin(base, "/favicon.png"), "favicon PNG default"),
        (90, urljoin(base, "/favicon.ico"), "favicon ICO default"),
    ]
    candidates.extend(defaults)

    proxy = (
        "https://www.google.com/s2/favicons?domain_url="
        + quote("https://" + domain + "/", safe="")
        + "&sz=256"
    )
    candidates.append((75, proxy, "official-domain favicon proxy fallback"))

    seen = set()
    out = []
    for row in sorted(candidates, key=lambda x: x[0], reverse=True):
        url = row[1]
        if url in seen or not url.lower().startswith("https://"):
            continue
        seen.add(url)
        out.append(row)
    return out


def clean_svg(body: bytes) -> bytes | None:
    try:
        text = body.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return None
    if "<svg" not in text.lower():
        return None
    text = re.sub(r"<script\b[^>]*>.*?</script\s*>", "", text, flags=re.I | re.S)
    text = re.sub(r'\\son[a-z]+\\s*=\\s*"[^"]*"', "", text, flags=re.I | re.S)
    text = re.sub(r"\\son[a-z]+\\s*=\\s*'[^']*'", "", text, flags=re.I | re.S)
    return text.encode("utf-8")


def raster_dimensions(body: bytes) -> tuple[int, int] | None:
    try:
        with Image.open(BytesIO(body)) as image:
            return image.size
    except Exception:
        return None


def raster_score(width: int, height: int, base_score: int) -> int | None:
    short = min(width, height)
    long = max(width, height)
    if short < MIN_RASTER_SIDE:
        return None
    if long / max(short, 1) > 3.2:
        return None
    quality = min(short, 512)
    if short >= GOOD_RASTER_SIDE:
        quality += 120
    return base_score + quality


def normalize_raster(body: bytes) -> bytes:
    with Image.open(BytesIO(body)) as source:
        image = ImageOps.exif_transpose(source).convert("RGBA")

    alpha_bbox = image.getchannel("A").getbbox()
    if alpha_bbox:
        image = image.crop(alpha_bbox)

    if image.width and image.height:
        corner = image.getpixel((0, 0))
        if corner[3] > 240 and min(corner[:3]) > 242:
            background = Image.new("RGBA", image.size, corner)
            diff = ImageChops.difference(image, background).convert("L")
            mask = diff.point(lambda x: 255 if x > 16 else 0)
            bbox = mask.getbbox()
            if bbox:
                content_area = max(1, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))
                whole_area = max(1, image.width * image.height)
                if content_area / whole_area >= 0.04:
                    image = image.crop(bbox)

    max_inner = int(OUTPUT_SIZE * 0.84)
    image.thumbnail((max_inner, max_inner), Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", (OUTPUT_SIZE, OUTPUT_SIZE), (255, 255, 255, 0))
    x = (OUTPUT_SIZE - image.width) // 2
    y = (OUTPUT_SIZE - image.height) // 2
    canvas.alpha_composite(image, (x, y))

    out = BytesIO()
    canvas.save(out, format="PNG", optimize=True)
    return out.getvalue()


def evaluate_remote_candidate(base_score: int, url: str, label: str):
    try:
        body, content_type, final_url = fetch(url, MAX_ICON)
        ext = sniff_ext(body, content_type, final_url)
        if ext == ".svg":
            cleaned = clean_svg(body)
            if cleaned and len(cleaned) >= 80:
                return base_score + 700, cleaned, ".svg", final_url, label, None
            return None
        if ext not in {".png", ".ico", ".jpg", ".jpeg", ".webp"}:
            return None
        dims = raster_dimensions(body)
        if not dims:
            return None
        score = raster_score(dims[0], dims[1], base_score)
        if score is None:
            return None
        normalized = normalize_raster(body)
        return score, normalized, ".png", final_url, label, dims
    except (HTTPError, URLError, ValueError, TimeoutError, OSError):
        return None
    except Exception:
        return None


def evaluate_local_vector(path_value: str):
    path = ROOT / str(path_value or "").strip()
    if not path.is_file() or path.suffix.lower() != ".svg":
        return None
    body = clean_svg(path.read_bytes())
    if not body:
        return None
    return 1450, body, ".svg", path.as_posix(), "curated crisp vector fallback", None


def resolve_icon(company: str, domain: str, direct_url: str = "", local_vector: str = ""):
    local = evaluate_local_vector(local_vector)
    if local:
        return local

    for base_score, url, label in candidate_urls(domain, direct_url):
        result = evaluate_remote_candidate(base_score, url, label)
        if result:
            return result

    return None


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Re-evaluate already cached company icons")
    args = parser.parse_args()

    jobs = load_json(JOBS_PATH, [])
    if not isinstance(jobs, list):
        raise SystemExit("data/jobs.json must be a JSON array")

    overrides = load_json(DOMAIN_PATH, {})
    direct_assets = load_json(DIRECT_PATH, {})
    quality_fallbacks = load_json(QUALITY_FALLBACK_PATH, {})
    manifest = load_json(MANIFEST_PATH, {})
    if not isinstance(manifest, dict):
        manifest = {}

    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    companies: dict[str, dict] = {}
    for job in jobs:
        company = str(job.get("company", "")).strip()
        if company and company not in companies:
            companies[company] = job

    changed = False
    resolved = 0
    failed = 0

    def work(item):
        company, sample = item
        domain = official_domain(sample, overrides)
        if not domain:
            return company, domain, None, "no trusted official domain"

        cached = manifest.get(company, {}) if isinstance(manifest.get(company), dict) else {}
        cached_path = str(cached.get("localPath", "")).strip()
        target_exists = bool(cached_path and (ROOT / cached_path).exists())
        direct_url = str(direct_assets.get(company, "")).strip()
        local_vector = str(quality_fallbacks.get(company, "")).strip()
        cached_source = str(cached.get("sourceType", "")).lower()
        quality_upgrade_needed = bool(local_vector) or bool(direct_url and "high-resolution" not in cached_source)

        if not args.refresh and target_exists and str(cached.get("officialDomain", "")) == domain and not quality_upgrade_needed:
            return company, domain, ("cache", cached_path, cached), ""

        result = resolve_icon(
            company,
            domain,
            direct_url,
            local_vector,
        )
        if result:
            return company, domain, ("resolved", result, cached), ""
        if target_exists:
            return company, domain, ("cache", cached_path, cached), ""
        return company, domain, None, "no quality-approved official icon found"

    items = sorted(companies.items(), key=lambda x: x[0].lower())
    results = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(work, item): item[0] for item in items}
        for future in as_completed(futures):
            company = futures[future]
            try:
                results[company] = future.result()
            except Exception as exc:
                results[company] = (company, "", None, type(exc).__name__)

    for company, _sample in items:
        _, domain, payload, error = results[company]
        cached_path = ""

        if not payload:
            failed += 1
            print(f"[MISS] {company}: {error}")
            continue

        kind = payload[0]
        if kind == "resolved":
            score, body, ext, source_url, source_type, dims = payload[1]
            stem = slugify(company)
            for old in ASSET_DIR.glob(stem + ".*"):
                old.unlink()
            target = ASSET_DIR / (stem + ext)
            target.write_bytes(body)
            local_path = target.relative_to(ROOT).as_posix()
            manifest[company] = {
                "officialDomain": domain,
                "sourceUrl": source_url,
                "sourceType": source_type,
                "localPath": local_path,
                "sourceDimensions": list(dims) if dims else None,
                "qualityScore": score,
                "bytes": len(body),
            }
            cached_path = local_path
            changed = True
            resolved += 1
            dims_text = f" {dims[0]}x{dims[1]}" if dims else " vector"
            print(f"[OK] {company}:{dims_text} {source_type} -> {local_path}")
        else:
            cached_path = payload[1]
            resolved += 1
            print(f"[CACHE] {company}: {cached_path}")

        if cached_path:
            for job in jobs:
                if str(job.get("company", "")).strip() == company:
                    if job.get("logoPath") != cached_path:
                        job["logoPath"] = cached_path
                        changed = True
                    if domain and job.get("logoSourceDomain") != domain:
                        job["logoSourceDomain"] = domain
                        changed = True

    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    JOBS_PATH.write_text(json.dumps(jobs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Quality-approved/cached: {resolved}; unresolved: {failed}; changed: {changed}")


if __name__ == "__main__":
    main()
