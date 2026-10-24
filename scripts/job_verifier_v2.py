"""HD Careers V2 shadow verifier.

This module never changes job status or publishes anything. It collects identity-bound,
time-stamped evidence from provider-specific adapters and derives an expiring verdict.
Initial adapters: Greenhouse and Lever.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
import ipaddress
import json
from pathlib import Path
import re
import socket
from typing import Literal
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
UA = "HD-Careers-Shadow-Verifier/2.0"
FORM = re.compile(r"<form\\b|apply for this job|submit application|application form", re.I)
CLOSED = re.compile(r"no longer (?:available|posted|accepting applications)|position has been filled|job has been filled|applications? (?:are |is )?closed", re.I)

State = Literal["LIVE", "EXPIRED", "UNCONFIRMED"]
AUTO_LIVE_PROVIDERS = frozenset({"greenhouse", "lever", "ashby", "smartrecruiters"})
REVIEW_ONLY_PROVIDERS = frozenset({"workday", "oracle_hcm", "successfactors", "phenom"})
Polarity = Literal["open", "closed", "neutral", "blocked", "error"]
Tier = Literal["A", "B", "C"]


@dataclass(frozen=True)
class ProviderRef:
    provider: str
    tenant: str
    requisition_id: str
    source_url: str


@dataclass
class Evidence:
    provider: str
    adapter: str
    method: str
    tier: Tier
    observed_at: str
    expected_requisition_id: str
    found_requisition_id: str | None
    identity_match: str
    polarity: Polarity
    code: str
    url: str
    final_url: str | None = None
    http_status: int | None = None
    detail: str = ""


@dataclass
class Verdict:
    state: State
    assurance: str
    provider: str | None
    requisition_id: str | None
    decided_at: str
    valid_until: str | None
    reasons: list[str]
    evidence: list[Evidence]


class Redirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Visible(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "template", "noscript"}:
            self.skip += 1
    def handle_endtag(self, tag):
        if tag in {"script", "style", "template", "noscript"}:
            self.skip = max(0, self.skip - 1)
    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def now_utc():
    return datetime.now(timezone.utc)


def safe_url(url: str):
    p = urlsplit(url)
    if p.scheme != "https" or not p.hostname or p.username or p.password or p.port not in (None, 443):
        raise ValueError("Only public HTTPS URLs are supported")
    addresses = socket.getaddrinfo(p.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(x[4][0]).is_global for x in addresses):
        raise ValueError("Non-public destination refused")


def request(url: str, accept: str):
    safe_url(url)
    req = Request(url, headers={"User-Agent": UA, "Accept": accept, "Accept-Language": "en-US,en;q=0.9"})
    with build_opener(Redirects()).open(req, timeout=20) as res:
        raw = res.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("Response exceeds inspection limit")
        return res.status, res.url, dict(res.headers.items()), raw.decode("utf-8", errors="replace")


def fetch_json(url: str):
    status, final_url, headers, body = request(url, "application/json")
    return status, final_url, headers, json.loads(body)


def fetch_html(url: str):
    return request(url, "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8")


def resolve(url: str) -> ProviderRef | None:
    p = urlsplit(url)
    host = (p.hostname or "").lower()
    parts = [x for x in p.path.split("/") if x]
    if host.endswith("greenhouse.io") and "jobs" in parts:
        i = parts.index("jobs")
        if i >= 1 and i + 1 < len(parts):
            return ProviderRef("greenhouse", parts[i - 1], parts[i + 1], url)
    if host == "jobs.lever.co" and len(parts) >= 2:
        return ProviderRef("lever", parts[0], parts[1], url)
    if host == "jobs.smartrecruiters.com" and len(parts) >= 2:
        posting_id = parts[1].split("-", 1)[0]
        if posting_id:
            return ProviderRef("smartrecruiters", parts[0], posting_id, url)
    if host == "jobs.ashbyhq.com" and len(parts) >= 2:
        return ProviderRef("ashby", parts[0], parts[1], url)
    if host.endswith(".myworkdayjobs.com") and "job" in parts:
        rid = parts[-1].rsplit("_", 1)[-1] if "_" in parts[-1] else ""
        if rid:
            return ProviderRef("workday", host.split(".", 1)[0], rid, url)
    if host.endswith("oraclecloud.com") and "CandidateExperience" in parts and "sites" in parts and "job" in parts:
        i = parts.index("sites")
        j = parts.index("job")
        if i + 1 < len(parts) and j + 1 < len(parts):
            return ProviderRef("oracle_hcm", f"{host}|{parts[i + 1]}", parts[j + 1], url)
    return None


def successfactors_ref(url: str) -> ProviderRef | None:
    """Recognize branded SAP SuccessFactors Career Site Builder pages without company allowlists."""
    safe_url(url)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=UA)
            signals = []
            page.on("response", lambda r: signals.append(r.url) if ("successfactors" in r.url.lower() or "/platform/js/j2w/" in r.url.lower()) else None)
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(700)
            final_url = page.url
            html = page.content()
            browser.close()
        blob = " ".join([url, final_url, html[:300000], *signals])
        if not re.search(r"successfactors|/platform/js/j2w/|rmkcdn\.successfactors\.com", blob, re.I):
            return None
        parts = [x for x in urlsplit(final_url).path.split("/") if x]
        rid = None
        for part in reversed(parts):
            m = re.fullmatch(r"(\d{4,})-(?:en_[A-Z]{2}|[a-z]{2}_[A-Z]{2})", part)
            if m:
                rid = m.group(1)
                break
            if re.fullmatch(r"\d{4,}", part):
                rid = part
                break
        if not rid:
            return None
        return ProviderRef("successfactors", (urlsplit(final_url).hostname or "").lower(), rid, url)
    except Exception:
        return None


def phenom_ref(url: str) -> ProviderRef | None:
    """Recognize Phenom-backed branded career pages from live network evidence."""
    safe_url(url)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=UA)
            signals = []
            page.on("response", lambda r: signals.append(r.url) if "phenompeople" in r.url.lower() else None)
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(700)
            final_url = page.url
            browser.close()
        if not signals:
            return None
        path = [x for x in urlsplit(final_url).path.split("/") if x]
        rid = None
        if "job" in [x.lower() for x in path]:
            i = [x.lower() for x in path].index("job")
            if i + 1 < len(path):
                rid = path[i + 1]
        if not rid:
            q = urlsplit(final_url).query
            m = re.search(r"(?:jobId|jobid)=([^&]+)", q, re.I)
            rid = m.group(1) if m else None
        if not rid:
            return None
        return ProviderRef("phenom", (urlsplit(final_url).hostname or "").lower(), rid, url)
    except Exception:
        return None


def resolve_dynamic(url: str) -> ProviderRef | None:
    direct = resolve(url)
    if direct:
        return direct
    for detector in (successfactors_ref, phenom_ref):
        try:
            ref = detector(url)
        except Exception:
            ref = None
        if ref:
            return ref
    return None


def ev(ref: ProviderRef, method: str, tier: Tier, polarity: Polarity, code: str, url: str,
       observed_at: datetime, found: str | None = None, final_url: str | None = None,
       status: int | None = None, detail: str = ""):
    match = "exact" if found and found.casefold() == ref.requisition_id.casefold() else ("none" if not found else "mismatch")
    return Evidence(ref.provider, f"{ref.provider}-v1", method, tier, observed_at.isoformat(),
                    ref.requisition_id, found, match, polarity, code, url, final_url, status, detail)


def visible_text(body: str):
    p = Visible()
    p.feed(body)
    return re.sub(r"\s+", " ", " ".join(p.parts)).strip()


def greenhouse_collect(ref: ProviderRef, observed_at: datetime):
    out = []
    api = f"https://boards-api.greenhouse.io/v1/boards/{ref.tenant}/jobs/{ref.requisition_id}"
    try:
        status, final_url, _, data = fetch_json(api)
        found = str(data.get("id", "")) if isinstance(data, dict) else None
        if status == 200 and found == ref.requisition_id:
            out.append(ev(ref, "api", "B", "open", "greenhouse.exact_record", api, observed_at, found, final_url, status))
            apply_url = str(data.get("absolute_url") or ref.source_url)
        else:
            out.append(ev(ref, "api", "B", "neutral", "greenhouse.unexpected_record", api, observed_at, found, final_url, status))
            return out
    except HTTPError as exc:
        if exc.code in (404, 410):
            out.append(ev(ref, "api", "A", "closed", f"greenhouse.api_{exc.code}", api, observed_at, ref.requisition_id, api, exc.code))
        else:
            out.append(ev(ref, "api", "B", "error", f"greenhouse.api_{exc.code}", api, observed_at, status=exc.code))
        return out
    except Exception as exc:
        out.append(ev(ref, "api", "B", "error", "greenhouse.api_error", api, observed_at, detail=type(exc).__name__))
        return out

    try:
        status, final_url, _, body = fetch_html(apply_url)
        text = visible_text(body)
        if CLOSED.search(text):
            out.append(ev(ref, "http", "A", "closed", "greenhouse.apply_closed", apply_url, observed_at, ref.requisition_id, final_url, status))
        elif status == 200 and FORM.search(body + " " + text) and (ref.requisition_id in final_url or ref.requisition_id in body):
            out.append(ev(ref, "http", "A", "open", "greenhouse.apply_form", apply_url, observed_at, ref.requisition_id, final_url, status))
        else:
            out.append(ev(ref, "http", "B", "neutral", "greenhouse.apply_unproven", apply_url, observed_at, None, final_url, status))
    except HTTPError as exc:
        out.append(ev(ref, "http", "B", "error", f"greenhouse.apply_http_{exc.code}", apply_url, observed_at, status=exc.code))
    except Exception as exc:
        out.append(ev(ref, "http", "B", "error", "greenhouse.apply_error", apply_url, observed_at, detail=type(exc).__name__))
    return out


def lever_collect(ref: ProviderRef, observed_at: datetime):
    out = []
    api = f"https://api.lever.co/v0/postings/{ref.tenant}/{ref.requisition_id}"
    try:
        status, final_url, _, data = fetch_json(api)
        found = str(data.get("id", "")) if isinstance(data, dict) else None
        if status == 200 and found.casefold() == ref.requisition_id.casefold():
            out.append(ev(ref, "api", "B", "open", "lever.exact_record", api, observed_at, found, final_url, status))
            apply_url = str(data.get("applyUrl") or f"https://jobs.lever.co/{ref.tenant}/{ref.requisition_id}/apply")
        else:
            out.append(ev(ref, "api", "B", "neutral", "lever.unexpected_record", api, observed_at, found, final_url, status))
            return out
    except HTTPError as exc:
        if exc.code in (404, 410):
            out.append(ev(ref, "api", "A", "closed", f"lever.api_{exc.code}", api, observed_at, ref.requisition_id, api, exc.code))
        else:
            out.append(ev(ref, "api", "B", "error", f"lever.api_{exc.code}", api, observed_at, status=exc.code))
        return out
    except Exception as exc:
        out.append(ev(ref, "api", "B", "error", "lever.api_error", api, observed_at, detail=type(exc).__name__))
        return out

    try:
        status, final_url, _, body = fetch_html(apply_url)
        text = visible_text(body)
        same = ref.requisition_id.casefold() in (final_url + " " + body).casefold()
        if CLOSED.search(text):
            out.append(ev(ref, "http", "A", "closed", "lever.apply_closed", apply_url, observed_at, ref.requisition_id, final_url, status))
        elif status == 200 and FORM.search(body + " " + text) and same:
            out.append(ev(ref, "http", "A", "open", "lever.apply_form", apply_url, observed_at, ref.requisition_id, final_url, status))
        else:
            out.append(ev(ref, "http", "B", "neutral", "lever.apply_unproven", apply_url, observed_at, None, final_url, status))
    except HTTPError as exc:
        out.append(ev(ref, "http", "B", "error", f"lever.apply_http_{exc.code}", apply_url, observed_at, status=exc.code))
    except Exception as exc:
        out.append(ev(ref, "http", "B", "error", "lever.apply_error", apply_url, observed_at, detail=type(exc).__name__))
    return out




def smartrecruiters_browser_probe(url: str, requisition_id: str):
    safe_url(url)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return "unavailable", url, ""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=UA)
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(800)
            before = page.locator("body").inner_text(timeout=5000)
            if CLOSED.search(before):
                final_url = page.url
                browser.close()
                return "closed", final_url, before[:500]
            interested = page.get_by_text(re.compile(r"^I'm interested$", re.I))
            if interested.count():
                interested.first.click(timeout=5000)
                page.wait_for_timeout(1000)
            text = page.locator("body").inner_text(timeout=5000)
            final_url = page.url
            fields = page.locator("input, textarea, select").count()
            application_words = re.search(r"first name|last name|email|phone|resume|upload|submit", text, re.I) is not None
            browser.close()
        if CLOSED.search(text):
            return "closed", final_url, text[:500]
        if fields >= 2 and application_words:
            return "open", final_url, text[:500]
        return "neutral", final_url, text[:500]
    except Exception as exc:
        return "error", url, type(exc).__name__

def smartrecruiters_collect(ref: ProviderRef, observed_at: datetime):
    out = []
    api = f"https://api.smartrecruiters.com/v1/companies/{ref.tenant}/postings/{ref.requisition_id}"
    try:
        status, final_url, _, data = fetch_json(api)
        found = str(data.get("id") or data.get("uuid") or "") if isinstance(data, dict) else None
        if status != 200 or not found or found.casefold() != ref.requisition_id.casefold():
            out.append(ev(ref, "api", "B", "neutral", "smartrecruiters.unexpected_record", api, observed_at, found, final_url, status))
            return out
        blob = json.dumps(data, ensure_ascii=False)
        if data.get("active") is False or CLOSED.search(blob):
            out.append(ev(ref, "api", "A", "closed", "smartrecruiters.explicit_closed", api, observed_at, found, final_url, status))
            return out
        out.append(ev(ref, "api", "B", "open", "smartrecruiters.current_posting", api, observed_at, found, final_url, status))
        apply_url = str(data.get("applyUrl") or ref.source_url)
        bstate, bfinal, bdetail = smartrecruiters_browser_probe(apply_url, ref.requisition_id)
        if bstate == "open":
            out.append(ev(ref, "browser", "A", "open", "smartrecruiters.apply_form", apply_url, observed_at, ref.requisition_id, bfinal, 200))
        elif bstate == "closed":
            out.append(ev(ref, "browser", "A", "closed", "smartrecruiters.apply_closed", apply_url, observed_at, ref.requisition_id, bfinal, 200))
        else:
            out.append(ev(ref, "browser", "B", "neutral" if bstate in ("neutral", "unavailable") else "error",
                          f"smartrecruiters.browser_{bstate}", apply_url, observed_at, None, bfinal, detail=bdetail))
    except HTTPError as exc:
        if exc.code in (404, 410):
            out.append(ev(ref, "api", "A", "closed", f"smartrecruiters.api_{exc.code}", api, observed_at, ref.requisition_id, api, exc.code))
        else:
            out.append(ev(ref, "api", "B", "error", f"smartrecruiters.api_{exc.code}", api, observed_at, status=exc.code))
    except Exception as exc:
        out.append(ev(ref, "api", "B", "error", "smartrecruiters.api_error", api, observed_at, detail=type(exc).__name__))
    return out

def browser_form_probe(url: str, requisition_id: str):
    safe_url(url)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return "unavailable", url, ""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=UA)
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(1200)
            final_url = page.url
            text = page.locator("body").inner_text(timeout=5000)
            has_form = page.locator("form").count() > 0
            has_fields = page.locator("input, textarea, select").count() >= 2
            has_submit = page.get_by_text(re.compile(r"submit application|apply", re.I)).count() > 0
            browser.close()
        if CLOSED.search(text):
            return "closed", final_url, text[:500]
        if requisition_id.casefold() in final_url.casefold() and (has_form or (has_fields and has_submit)):
            return "open", final_url, text[:500]
        return "neutral", final_url, text[:500]
    except Exception as exc:
        return "error", url, type(exc).__name__

def ashby_collect(ref: ProviderRef, observed_at: datetime):
    out = []
    api = f"https://api.ashbyhq.com/posting-api/job-board/{ref.tenant}"
    try:
        status, final_url, _, data = fetch_json(api)
        jobs = data.get("jobs", []) if isinstance(data, dict) else []
        exact = None
        for item in jobs:
            blob = " ".join(str(item.get(k, "")) for k in ("jobUrl", "applyUrl"))
            if ref.requisition_id.casefold() in blob.casefold():
                exact = item
                break
        if exact is None:
            out.append(ev(ref, "api", "A", "closed", "ashby.absent_from_current_board", api, observed_at, ref.requisition_id, final_url, status,
                          "Exact requisition is absent from Ashby's official currently-published job board API."))
            return out
        out.append(ev(ref, "api", "B", "open", "ashby.current_public_posting", api, observed_at, ref.requisition_id, final_url, status))
        apply_url = str(exact.get("applyUrl") or "")
        if not apply_url:
            out.append(ev(ref, "api", "B", "neutral", "ashby.no_apply_url", api, observed_at, ref.requisition_id, final_url, status))
            return out
        try:
            hstatus, hfinal, _, body = fetch_html(apply_url)
            text = visible_text(body)
            same = ref.requisition_id.casefold() in (hfinal + " " + body).casefold()
            if CLOSED.search(text):
                out.append(ev(ref, "http", "A", "closed", "ashby.apply_closed", apply_url, observed_at, ref.requisition_id, hfinal, hstatus))
            elif hstatus == 200 and FORM.search(body + " " + text) and same:
                out.append(ev(ref, "http", "A", "open", "ashby.apply_form", apply_url, observed_at, ref.requisition_id, hfinal, hstatus))
            else:
                out.append(ev(ref, "http", "B", "neutral", "ashby.apply_unproven", apply_url, observed_at, None, hfinal, hstatus))
                bstate, bfinal, bdetail = browser_form_probe(apply_url, ref.requisition_id)
                if bstate == "open":
                    out.append(ev(ref, "browser", "A", "open", "ashby.browser_apply_form", apply_url, observed_at, ref.requisition_id, bfinal, 200))
                elif bstate == "closed":
                    out.append(ev(ref, "browser", "A", "closed", "ashby.browser_apply_closed", apply_url, observed_at, ref.requisition_id, bfinal, 200))
                else:
                    out.append(ev(ref, "browser", "B", "neutral" if bstate in ("neutral", "unavailable") else "error",
                                  f"ashby.browser_{bstate}", apply_url, observed_at, None, bfinal, detail=bdetail))
        except HTTPError as exc:
            out.append(ev(ref, "http", "B", "error", f"ashby.apply_http_{exc.code}", apply_url, observed_at, status=exc.code))
        except Exception as exc:
            out.append(ev(ref, "http", "B", "error", "ashby.apply_error", apply_url, observed_at, detail=type(exc).__name__))
    except HTTPError as exc:
        out.append(ev(ref, "api", "B", "error", f"ashby.board_http_{exc.code}", api, observed_at, status=exc.code))
    except Exception as exc:
        out.append(ev(ref, "api", "B", "error", "ashby.board_error", api, observed_at, detail=type(exc).__name__))
    return out


def workday_browser_probe(url: str, requisition_id: str):
    safe_url(url)
    apply_url = url.split("?", 1)[0].rstrip("/") + "/apply/applyManually"
    safe_url(apply_url)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return "unavailable", url, ""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=UA)
            page.goto(apply_url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(1500)
            text = page.locator("body").inner_text(timeout=5000)
            final_url = page.url
            has_fields = page.locator("input, textarea, select").count() >= 2
            has_auth = re.search(r"create account|sign in|email address|password", text, re.I) is not None
            has_start = re.search(r"start your application|autofill with resume|apply manually|use my last application", text, re.I) is not None
            has_application = re.search(r"my information|my experience|application questions|resume|review", text, re.I) is not None
            exact = requisition_id.casefold() in (final_url + " " + text).casefold()
            browser.close()
        if CLOSED.search(text):
            return "closed", final_url, text[:500]
        if has_auth or has_start or has_application or (exact and has_fields):
            return "open", final_url, text[:500]
        if not exact:
            return "closed", final_url, text[:500]
        return "neutral", final_url, text[:500]
    except Exception as exc:
        return "error", apply_url, type(exc).__name__

def workday_collect(ref: ProviderRef, observed_at: datetime):
    out = []
    p = urlsplit(ref.source_url)
    parts = [x for x in p.path.split("/") if x]
    try:
        i = parts.index("job")
        board = parts[i - 1]
        tail = "/".join(parts[i:])
        cxs = f"https://{p.hostname}/wday/cxs/{ref.tenant}/{board}/{tail}"
        try:
            status, final_url, _, data = fetch_json(cxs)
            blob = json.dumps(data, ensure_ascii=False)
            if status == 200 and ref.requisition_id.casefold() in blob.casefold():
                info = data.get("jobPostingInfo", {}) if isinstance(data, dict) else {}
                can_apply = info.get("canApply") if isinstance(info, dict) else None
                if can_apply is True:
                    out.append(ev(ref, "cxs", "A", "open", "workday.cxs_can_apply_true", cxs, observed_at, ref.requisition_id, final_url, status))
                elif can_apply is False:
                    out.append(ev(ref, "cxs", "A", "closed", "workday.cxs_can_apply_false", cxs, observed_at, ref.requisition_id, final_url, status))
                else:
                    out.append(ev(ref, "cxs", "B", "open", "workday.cxs_exact_record", cxs, observed_at, ref.requisition_id, final_url, status))
            else:
                out.append(ev(ref, "cxs", "B", "neutral", "workday.cxs_unproven", cxs, observed_at, None, final_url, status))
        except HTTPError as exc:
            out.append(ev(ref, "cxs", "B", "neutral", f"workday.cxs_http_{exc.code}", cxs, observed_at, status=exc.code))
        except Exception as exc:
            out.append(ev(ref, "cxs", "B", "error", "workday.cxs_error", cxs, observed_at, detail=type(exc).__name__))
    except (ValueError, IndexError):
        out.append(ev(ref, "cxs", "B", "error", "workday.cxs_unresolved", ref.source_url, observed_at))

    bstate, bfinal, bdetail = workday_browser_probe(ref.source_url, ref.requisition_id)
    if bstate == "open":
        out.append(ev(ref, "browser", "B", "open", "workday.generic_application_flow", ref.source_url, observed_at, ref.requisition_id, bfinal, 200,
                      "Workday may expose a generic application/login flow for stale requisitions; this signal cannot prove LIVE."))
    elif bstate == "closed":
        out.append(ev(ref, "browser", "A", "closed", "workday.browser_closed", ref.source_url, observed_at, ref.requisition_id, bfinal, 200))
    else:
        out.append(ev(ref, "browser", "B", "neutral" if bstate in ("neutral", "unavailable") else "error",
                      f"workday.browser_{bstate}", ref.source_url, observed_at, None, bfinal, detail=bdetail))
    return out


def oracle_browser_probe(url: str, requisition_id: str):
    safe_url(url)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return "unavailable", url, ""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=UA)
            requisition_detail = []

            def capture_response(response):
                if "recruitingCEJobRequisitionDetails" not in response.url:
                    return
                try:
                    data = response.json()
                    items = data.get("items", []) if isinstance(data, dict) else []
                    if not items:
                        requisition_detail.append(("closed", response.url, "exact Oracle CE requisition details returned no items"))
                        return
                    blob = json.dumps(items, ensure_ascii=False)
                    if requisition_id.casefold() in blob.casefold():
                        requisition_detail.append(("open", response.url, "exact Oracle CE requisition details returned current requisition"))
                    else:
                        requisition_detail.append(("mismatch", response.url, "Oracle CE requisition details returned a different requisition"))
                except Exception as exc:
                    requisition_detail.append(("error", response.url, type(exc).__name__))

            page.on("response", capture_response)
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(1800)
            text = page.locator("body").inner_text(timeout=5000)
            final_url = page.url

            exact_states = [x for x in requisition_detail if x[0] in ("open", "closed", "mismatch")]
            if exact_states:
                state, endpoint, detail = exact_states[-1]
                browser.close()
                return state, endpoint, detail

            if CLOSED.search(text):
                browser.close()
                return "closed", final_url, text[:500]

            browser.close()
            return "neutral", final_url, text[:500]
    except Exception as exc:
        return "error", url, type(exc).__name__


def oracle_collect(ref: ProviderRef, observed_at: datetime):
    out = []
    p = urlsplit(ref.source_url)
    bstate, bfinal, bdetail = oracle_browser_probe(ref.source_url, ref.requisition_id)
    if bstate == "closed":
        out.append(ev(ref, "browser", "A", "closed", "oracle.exact_requisition_absent", ref.source_url, observed_at, ref.requisition_id, bfinal, 200))
    elif bstate == "open":
        out.append(ev(ref, "browser", "A", "open", "oracle.exact_requisition_present", ref.source_url, observed_at, ref.requisition_id, bfinal, 200))
    else:
        out.append(ev(ref, "browser", "B", "neutral" if bstate in ("neutral", "unavailable") else "error",
                      f"oracle.browser_{bstate}", ref.source_url, observed_at, None, bfinal, detail=bdetail))
    return out

def successfactors_collect(ref: ProviderRef, observed_at: datetime):
    out = []
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return [ev(ref, "browser", "B", "error", "successfactors.browser_unavailable", ref.source_url, observed_at)]
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=UA)
            page.goto(ref.source_url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(900)
            text = page.locator("body").inner_text(timeout=5000)
            final_url = page.url
            browser.close()
        exact = ref.requisition_id.casefold() in final_url.casefold()
        unavailable = re.search(r"you can['’]?t view this job because it['’]?s not available at this time|job is not available at this time|position is no longer available", text, re.I)
        apply_now = re.search(r"\bapply now\b", text, re.I)
        if unavailable and exact:
            out.append(ev(ref, "browser", "A", "closed", "successfactors.exact_job_unavailable", ref.source_url, observed_at, ref.requisition_id, final_url, 200))
        elif exact and apply_now and len(text) > 500:
            out.append(ev(ref, "browser", "A", "open", "successfactors.exact_job_apply_present", ref.source_url, observed_at, ref.requisition_id, final_url, 200,
                          "Exact SuccessFactors job renders role content and Apply now; provider remains review-only until calibrated."))
        else:
            out.append(ev(ref, "browser", "B", "neutral", "successfactors.unproven", ref.source_url, observed_at, ref.requisition_id if exact else None, final_url, 200))
    except Exception as exc:
        out.append(ev(ref, "browser", "B", "error", "successfactors.browser_error", ref.source_url, observed_at, detail=type(exc).__name__))
    return out


def phenom_collect(ref: ProviderRef, observed_at: datetime):
    out = []
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return [ev(ref, "browser", "B", "error", "phenom.browser_unavailable", ref.source_url, observed_at)]
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=UA)
            phenom_signals = []
            page.on("response", lambda r: phenom_signals.append(r.url) if "phenompeople" in r.url.lower() else None)
            response = page.goto(ref.source_url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(900)
            status = response.status if response else None
            final_url = page.url
            try:
                text = page.locator("body").inner_text(timeout=5000)
            except Exception:
                text = ""
            browser.close()
        if not phenom_signals:
            out.append(ev(ref, "browser", "B", "neutral", "phenom.provider_not_proven", ref.source_url, observed_at, final_url=final_url, http_status=status))
            return out
        exact_url = ref.requisition_id.casefold() in final_url.casefold()
        exact_body = ref.requisition_id.casefold() in text.casefold()
        if status in {404, 410} and exact_url:
            out.append(ev(ref, "browser", "A", "closed", "phenom.exact_requisition_gone", ref.source_url, observed_at, ref.requisition_id, final_url, status,
                          "Exact Phenom-backed requisition returned HTTP 404/410."))
        elif status == 200 and exact_url and exact_body and re.search(r"\\bapply now\\b", text, re.I) and len(text) > 500:
            out.append(ev(ref, "browser", "A", "open", "phenom.exact_job_apply_present", ref.source_url, observed_at, ref.requisition_id, final_url, status,
                          "Exact Phenom-backed job renders matching requisition, role content and Apply Now; provider remains review-only."))
        else:
            out.append(ev(ref, "browser", "B", "neutral", "phenom.unproven", ref.source_url, observed_at, ref.requisition_id if exact_url else None, final_url, status))
    except Exception as exc:
        out.append(ev(ref, "browser", "B", "error", "phenom.browser_error", ref.source_url, observed_at, detail=type(exc).__name__))
    return out


def decide(ref: ProviderRef | None, evidence: list[Evidence], observed_at: datetime | None = None):
    t = observed_at or now_utc()
    if ref is None:
        return Verdict("UNCONFIRMED", "weak", None, None, t.isoformat(), None, ["unsupported_provider"], evidence)
    exact_a_closed = [x for x in evidence if x.tier == "A" and x.polarity == "closed" and x.identity_match == "exact"]
    exact_a_open = [x for x in evidence if x.tier == "A" and x.polarity == "open" and x.identity_match == "exact"]
    mismatch = [x for x in evidence if x.identity_match == "mismatch"]
    if exact_a_closed and exact_a_open:
        return Verdict("UNCONFIRMED", "weak", ref.provider, ref.requisition_id, t.isoformat(), None, ["conflicting_tier_a_evidence"], evidence)
    if exact_a_closed:
        return Verdict("EXPIRED", "proven", ref.provider, ref.requisition_id, t.isoformat(), None, [x.code for x in exact_a_closed], evidence)
    if exact_a_open and not mismatch:
        if ref.provider in REVIEW_ONLY_PROVIDERS or ref.provider not in AUTO_LIVE_PROVIDERS:
            return Verdict("UNCONFIRMED", "weak", ref.provider, ref.requisition_id, t.isoformat(), None,
                           ["provider_review_only", *[x.code for x in exact_a_open]], evidence)
        return Verdict("LIVE", "proven", ref.provider, ref.requisition_id, t.isoformat(), (t + timedelta(minutes=30)).isoformat(), [x.code for x in exact_a_open], evidence)
    return Verdict("UNCONFIRMED", "weak", ref.provider, ref.requisition_id, t.isoformat(), None, [x.code for x in evidence] or ["no_evidence"], evidence)


def verify_url(url: str, observed_at: datetime | None = None):
    t = observed_at or now_utc()
    ref = resolve_dynamic(url)
    if ref is None:
        return decide(None, [], t)
    collector = {"greenhouse": greenhouse_collect, "lever": lever_collect, "smartrecruiters": smartrecruiters_collect, "ashby": ashby_collect, "workday": workday_collect, "oracle_hcm": oracle_collect, "successfactors": successfactors_collect, "phenom": phenom_collect}[ref.provider]
    return decide(ref, collector(ref, t), t)


def main():
    parser = argparse.ArgumentParser(description="HD Careers V2 shadow verifier; never writes production job status")
    parser.add_argument("--jobs", default=str(ROOT / "data" / "jobs.json"))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output", default=str(ROOT / "shadow-verification-report.json"))
    args = parser.parse_args()
    jobs = json.loads(Path(args.jobs).read_text())
    supported = []
    for job in jobs:
        if job.get("status") == "active" and resolve_dynamic(str(job.get("apply", ""))):
            supported.append(job)
    if args.limit:
        supported = supported[:args.limit]
    rows = []
    for job in supported:
        verdict = verify_url(job["apply"])
        rows.append({"id": job.get("id"), "company": job.get("company"), "role": job.get("role"), **asdict(verdict)})
        print(f'{job.get("company")} / {job.get("role")}: {verdict.state} — {", ".join(verdict.reasons)}')
    report = {"shadow": True, "productionWrites": False, "checkedAt": now_utc().isoformat(), "checked": len(rows), "items": rows}
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
