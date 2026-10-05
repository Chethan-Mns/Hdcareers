from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
from html.parser import HTMLParser
import ipaddress
import json
from pathlib import Path
import re
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
JOBS_PATH = ROOT / "data" / "jobs.json"
DOMAIN_PATH = ROOT / "data" / "company-logo-domains.json"
MANIFEST_PATH = ROOT / "data" / "company-logos.json"
ASSET_DIR = ROOT / "assets" / "company-icons"

GENERIC_HOSTS = (
    "myworkdayjobs.com", "myworkdaysite.com", "greenhouse.io", "lever.co",
    "successfactors.com", "taleo.net", "oraclecloud.com", "icims.com",
    "smartrecruiters.com", "workable.com", "infosysapps.com",
)

USER_AGENT = "HD-Careers-Official-Logo-Resolver/1.0"
MAX_HTML = 1_500_000
MAX_ICON = 700_000


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
        href_lower = href.lower().split("?", 1)[0]
        if href_lower.endswith(".svg"):
            return
        sizes = data.get("sizes", "")
        score = 70
        if "apple-touch-icon" in rel:
            score = 110
        elif "shortcut icon" in rel:
            score = 85
        elif rel.strip() == "icon":
            score = 90
        match = re.search(r"(\d+)x(\d+)", sizes)
        if match:
            score += min(int(match.group(1)), int(match.group(2)), 256) // 8
        icon_type = data.get("type", "").lower()
        if "png" in icon_type:
            score += 8
        elif "ico" in icon_type or "x-icon" in icon_type:
            score += 4
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
        "Accept": "text/html,application/xhtml+xml,image/avif,image/webp,image/png,image/jpeg,image/x-icon,*/*;q=0.7",
    })
    with build_opener().open(req, timeout=7) as res:
        body = res.read(limit + 1)
        if len(body) > limit:
            raise ValueError("response too large")
        return body, str(res.headers.get("Content-Type", "")).lower(), res.geturl()


def sniff_ext(body: bytes, content_type: str, url: str) -> str:
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
    return suffix if suffix in {".png", ".ico", ".jpg", ".jpeg", ".webp"} else ""


def slugify(company: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", company.lower()).strip("-")[:70] or "company"
    digest = hashlib.sha1(company.encode("utf-8")).hexdigest()[:7]
    return f"{base}-{digest}"


def candidate_urls(domain: str) -> list[tuple[int, str, str]]:
    base = f"https://{domain}/"
    candidates: list[tuple[int, str, str]] = []
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
        (104, urljoin(base, "/apple-touch-icon.png"), "apple-touch-icon default"),
        (96, urljoin(base, "/favicon-192x192.png"), "favicon 192 default"),
        (92, urljoin(base, "/favicon-96x96.png"), "favicon 96 default"),
        (88, urljoin(base, "/favicon-32x32.png"), "favicon 32 default"),
        (82, urljoin(base, "/favicon.png"), "favicon png default"),
        (78, urljoin(base, "/favicon.ico"), "favicon ico default"),
    ]
    candidates.extend(defaults)

    seen = set()
    out = []
    for row in sorted(candidates, key=lambda x: x[0], reverse=True):
        url = row[1]
        if url in seen or not url.lower().startswith("https://"):
            continue
        seen.add(url)
        out.append(row)
    return out


def resolve_icon(company: str, domain: str) -> tuple[bytes, str, str, str] | None:
    for _, url, label in candidate_urls(domain)[:5]:
        try:
            body, content_type, final_url = fetch(url, MAX_ICON)
            ext = sniff_ext(body, content_type, final_url)
            if not ext or len(body) < 64:
                continue
            return body, ext, final_url, label
        except (HTTPError, URLError, ValueError, TimeoutError, OSError):
            continue
    return None


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Re-fetch already cached company icons")
    args = parser.parse_args()

    jobs = load_json(JOBS_PATH, [])
    if not isinstance(jobs, list):
        raise SystemExit("data/jobs.json must be a JSON array")
    overrides = load_json(DOMAIN_PATH, {})
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
        if not args.refresh and target_exists and str(cached.get("officialDomain", "")) == domain:
            return company, domain, ("cache", cached_path, cached), ""
        result = resolve_icon(company, domain)
        if result:
            return company, domain, ("resolved", result, cached), ""
        if target_exists:
            return company, domain, ("cache", cached_path, cached), ""
        return company, domain, None, "no usable official icon found"

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

    for company, sample in items:
        _, domain, payload, error = results[company]
        cached_path = ""
        if not payload:
            failed += 1
            print(f"[MISS] {company}: {error}")
            continue

        kind = payload[0]
        if kind == "resolved":
            body, ext, source_url, source_type = payload[1]
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
                "bytes": len(body),
            }
            cached_path = local_path
            changed = True
            resolved += 1
            print(f"[OK] {company}: {source_url} -> {local_path}")
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
    print(f"Resolved/cached: {resolved}; unresolved: {failed}; changed: {changed}")


if __name__ == "__main__":
    main()
