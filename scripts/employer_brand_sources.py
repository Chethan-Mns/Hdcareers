"""Discover employer-owned brand assets without assuming an ATS provider owns the brand.

Parsing is deliberately conservative: the employer's verified corporate domain
is the source of truth, not the favicon of Workday, Lever, Oracle or Airtable.
"""
from __future__ import annotations

from html.parser import HTMLParser
import json
import re
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET


def normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").casefold())


def _asset_url(value) -> str:
    if isinstance(value, dict):
        value = value.get("url") or value.get("contentUrl") or value.get("@id")
    return value.strip() if isinstance(value, str) else ""


def _organization_logos(node, company: str) -> list[str]:
    """Read JSON-LD Organization.logo only when the organization matches the job employer."""
    if isinstance(node, list):
        return [v for obj in node for v in _organization_logos(obj, company)]
    if not isinstance(node, dict):
        return []
    found: list[str] = []
    typ = node.get("@type", "")
    kinds = {str(x).casefold() for x in (typ if isinstance(typ, list) else [typ])}
    if kinds.intersection({"organization", "corporation", "brand", "localbusiness"}):
        label = normalized_name(str(node.get("name", "")))
        employer = normalized_name(company)
        if label and employer and (label == employer or
            (len(employer) > 5 and label.startswith(employer))):
            logo = _asset_url(node.get("logo"))
            if logo:
                found.append(logo)
    for name in ("@graph", "mainEntity", "publisher", "hiringOrganization"):
        if name in node:
            found.extend(_organization_logos(node[name], company))
    return found


class EmployerBrandParser(HTMLParser):
    """Collect official-site logo candidates in quality/identity priority order."""
    def __init__(self, company: str):
        super().__init__(convert_charrefs=True)
        self.company = company
        self.company_key = normalized_name(company)
        self.assets: list[tuple[int, str, str]] = []
        self._header_depth = 0
        self._script_ld = False
        self._script_buffer: list[str] = []

    def handle_starttag(self, tag, attrs):
        tag = tag.casefold()
        data = {str(k).casefold(): str(v or "") for k, v in attrs}
        if tag in ("header", "nav"):
            self._header_depth += 1
        if tag == "script" and "ld+json" in data.get("type", "").casefold():
            self._script_ld = True
            self._script_buffer = []
        if tag == "meta":
            field = (data.get("property") or data.get("name") or data.get("itemprop") or "").casefold()
            if field in ("logo", "og:logo", "twitter:logo"):
                url = data.get("content", "")
                if url:
                    self.assets.append((990, url, "official site logo metadata"))
        if tag == "img":
            alt = data.get("alt", "").casefold()
            attrs_text = " ".join((data.get("class", ""), data.get("id", ""))).casefold()
            src = data.get("src") or data.get("data-src") or data.get("data-lazy-src") or ""
            if src.startswith("data:") or src.startswith("blob:"):
                src = data.get("data-src") or ""
            if src:
                alt_key = normalized_name(alt)
                named_brand = bool(self.company_key and self.company_key in alt_key)
                explicitly_logo = "logo" in alt or "logo" in attrs_text
                # A gallery of partner logos must not override the employer's own mark.
                if explicitly_logo and named_brand:
                    self.assets.append((960, src, "company-named logo image"))
                elif self._header_depth and explicitly_logo and not ("partner" in alt or "client" in alt):
                    self.assets.append((830, src, "employer site header logo"))
                elif self._header_depth and named_brand:
                    self.assets.append((800, src, "employer site branded header image"))
        if tag == "link":
            rel = data.get("rel", "").casefold()
            href = data.get("href", "").strip()
            if href and "icon" in rel:
                if "apple-touch-icon" in rel:
                    score = 430
                elif "mask-icon" in rel:
                    score = 425
                elif href.lower().split("?")[0].endswith(".svg"):
                    score = 410
                else:
                    score = 280
                dimensions = re.search(r"(\d+)x(\d+)", data.get("sizes", ""))
                if dimensions:
                    score += min(int(dimensions.group(1)), int(dimensions.group(2)), 512) // 4
                self.assets.append((score, href, "official employer-site icon"))

    def handle_endtag(self, tag):
        tag = tag.casefold()
        if tag in ("header", "nav"):
            self._header_depth = max(0, self._header_depth - 1)
        if tag == "script" and self._script_ld:
            try:
                value = json.loads("".join(self._script_buffer))
                for url in _organization_logos(value, self.company):
                    self.assets.append((1000, url, "matching Organization.logo JSON-LD"))
            except (ValueError, TypeError):
                pass
            self._script_ld = False
            self._script_buffer = []

    def handle_data(self, data):
        if self._script_ld and sum(map(len, self._script_buffer)) < 200_000:
            self._script_buffer.append(data)


def official_logo_candidates(html: str, base_url: str, company: str) -> list[tuple[int, str, str]]:
    parser = EmployerBrandParser(company)
    parser.feed(html[:1_500_000])
    out = []
    seen = set()
    for score, raw, origin in sorted(parser.assets, key=lambda x: -x[0]):
        url = urljoin(base_url, raw.strip())
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            continue
        if url not in seen:
            seen.add(url)
            out.append((score, url, origin))
    return out


SAFE_SVG_TAGS = {
    "svg", "g", "path", "rect", "circle", "ellipse", "polygon", "polyline",
    "line", "defs", "linearGradient", "radialGradient", "stop", "clipPath",
    "mask", "title", "desc", "style", "use", "symbol", "text", "tspan",
    "filter", "feGaussianBlur", "feOffset", "feMerge", "feMergeNode",
    "feColorMatrix", "feComposite", "feFlood", "feBlend", "pattern",
}


def safe_svg_bytes(body: bytes) -> bytes | None:
    """Reject executable or externally-referencing SVG; never publish untrusted markup."""
    try:
        raw = body.decode("utf-8")
        if len(raw) > 1_500_000 or "<!DOCTYPE" in raw.upper() or "<!ENTITY" in raw.upper():
            return None
        root = ET.fromstring(raw)
        if root.tag.split("}")[-1] != "svg":
            return None
        for node in root.iter():
            if node.tag.split("}")[-1] not in SAFE_SVG_TAGS:
                return None
            if node.tag.split("}")[-1] == "style":
                css = node.text or ""
                if "@import" in css.casefold() or re.search(r"url\(\s*(?!['\"]?#)", css, re.I):
                    return None
            for key, value in node.attrib.items():
                field = key.split("}")[-1].casefold()
                val = value.strip()
                if field.startswith("on"):
                    return None
                if field in ("href", "src") and not val.startswith("#"):
                    return None
                if re.search(r"javascript:|vbscript:|expression\s*\(|@import", val, re.I):
                    return None
                if "url(" in val.casefold() and re.search(r"url\(\s*(?!['\"]?#)", val, re.I):
                    return None
        ET.register_namespace("", "http://www.w3.org/2000/svg")
        return ET.tostring(root, encoding="utf-8")
    except (ValueError, ET.ParseError, UnicodeDecodeError):
        return None


class EmployerWebsiteLinkParser(HTMLParser):
    """Find a first-party employer URL explicitly attributed to the hiring company."""
    def __init__(self, company: str):
        super().__init__(convert_charrefs=True)
        self.company = normalized_name(company)
        self.sites: list[tuple[int, str]] = []
        self._anchor: str | None = None
        self._anchor_text: list[str] = []
        self._script_ld = False
        self._script_buffer: list[str] = []

    def handle_starttag(self, tag, attrs):
        values = {str(k).casefold(): str(v or "") for k, v in attrs}
        if tag.casefold() == "a":
            self._anchor = values.get("href", "")
            self._anchor_text = []
        if tag.casefold() == "script" and "ld+json" in values.get("type", "").casefold():
            self._script_ld = True
            self._script_buffer = []

    def handle_data(self, data):
        if self._anchor is not None and sum(map(len, self._anchor_text)) < 2000:
            self._anchor_text.append(data)
        if self._script_ld and sum(map(len, self._script_buffer)) < 200_000:
            self._script_buffer.append(data)

    def handle_endtag(self, tag):
        if tag.casefold() == "a" and self._anchor is not None:
            label = " ".join(self._anchor_text).casefold()
            key = normalized_name(label)
            if self.company and self.company in key and any(
                phrase in key for phrase in ("home", "website", "company", "about")
            ):
                self.sites.append((800, self._anchor))
            self._anchor = None
            self._anchor_text = []
        if tag.casefold() == "script" and self._script_ld:
            try:
                self.sites.extend((900, u) for u in hiring_company_urls(
                    json.loads("".join(self._script_buffer)), self.company))
            except (ValueError, TypeError):
                pass
            self._script_ld = False
            self._script_buffer = []


def hiring_company_urls(node, company_key: str) -> list[str]:
    if isinstance(node, list):
        return [url for item in node for url in hiring_company_urls(item, company_key)]
    if not isinstance(node, dict):
        return []
    found = []
    employer = node.get("hiringOrganization")
    if isinstance(employer, dict):
        name = normalized_name(str(employer.get("name", "")))
        if name and (name == company_key or
                (len(company_key) > 5 and name.startswith(company_key))):
            for field in ("url", "sameAs"):
                value = employer.get(field)
                if isinstance(value, str):
                    found.append(value)
    for child in ("@graph", "mainEntity", "itemListElement"):
        if child in node:
            found.extend(hiring_company_urls(node[child], company_key))
    return found


def employer_website_candidates(html: str, job_url: str, company: str) -> list[str]:
    parser = EmployerWebsiteLinkParser(company)
    parser.feed(html[:1_500_000])
    urls = []
    seen = set()
    for _score, raw in sorted(parser.sites, key=lambda x: -x[0]):
        url = urljoin(job_url, raw)
        parsed = urlparse(url)
        if parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password:
            if url not in seen:
                seen.add(url)
                urls.append(url)
    return urls
