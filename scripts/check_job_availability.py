"""Conservative official-page checks shared by monitoring and publishing."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
import ipaddress
import os
import json
from pathlib import Path
import re
import socket
import subprocess
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit, quote, urljoin
from urllib.request import Request, HTTPRedirectHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
REVIEW_QUEUE = ROOT / 'data' / 'review-queue.json'
CLOSED = re.compile(r'\b(?:this (?:job|position|vacancy) (?:is no longer available|has been filled|has expired|is closed)|no longer accepting applications|applications (?:are |have )?closed|job not found)\b', re.I)
APPLY = re.compile(r'\b(?:apply now|apply for (?:this|the) (?:job|role|position)|apply to (?:this|the) job|submit(?: application| response| form)?)\b', re.I)
BLOCKED = re.compile(r'\b(?:access denied|verify (?:that )?you are human|checking your browser|complete (?:the )?captcha|captcha (?:required|challenge)|security verification required)\b', re.I)
BROWSER_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36'
BOT_UA = 'HD-Careers-Availability/1.0'

class Visible(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style', 'template', 'noscript'}: self.skip += 1
    def handle_endtag(self, tag):
        if tag in {'script', 'style', 'template', 'noscript'}: self.skip = max(0, self.skip - 1)
    def handle_data(self, data):
        if not self.skip: self.parts.append(data)

def safe_url(url):
    p = urlsplit(url)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None, 443):
        raise ValueError('Only public HTTPS career URLs are supported')
    addresses = socket.getaddrinfo(p.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('Non-public destination refused')

class Redirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def deadline_passed(job, now):
    raw = job.get('closingAt')
    if not raw: return False
    dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    if dt.tzinfo is None: raise ValueError('closingAt requires an explicit timezone')
    return now >= dt

def manual_verification_fresh(job, now):
    manual = job.get('manualLiveVerifiedAt')
    if manual and job.get('manualLiveVerifiedUrl') != job.get('apply'):
        return False
    raw = manual or job.get('browserVerifiedAt')
    if not raw: return False
    try:
        dt = datetime.fromisoformat(str(raw).replace('Z', '+00:00'))
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        window = timedelta(hours=72 if manual else 24)
        return timedelta(0) <= now - dt <= window
    except Exception:
        return False


def fetch_json(url):
    safe_url(url)
    req = Request(url, headers={
        'User-Agent': BROWSER_UA,
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    with build_opener(Redirects()).open(req, timeout=20) as res:
        if res.status != 200:
            raise HTTPError(url, res.status, 'Unexpected status', res.headers, None)
        raw = res.read(2_000_001)
        if len(raw) > 2_000_000: raise ValueError('JSON response exceeds inspection size limit')
        return json.loads(raw.decode('utf-8', errors='replace'))

def official_inventory_probe(job):
    """Use public ATS inventories when the URL identifies a supported provider."""
    url = str(job.get('apply', '')).strip()
    p = urlsplit(url)
    host = (p.hostname or '').lower()
    parts = [x for x in p.path.split('/') if x]

    provider = endpoint = None
    expected_id = None
    try:
        if host.endswith('greenhouse.io') and 'jobs' in parts:
            i = parts.index('jobs')
            if i >= 1 and i + 1 < len(parts):
                board, expected_id = parts[i - 1], parts[i + 1]
                endpoint = f'https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{expected_id}'
                provider = 'Greenhouse'
        elif host == 'jobs.lever.co' and len(parts) >= 2:
            site, expected_id = parts[0], parts[1]
            endpoint = f'https://api.lever.co/v0/postings/{site}/{expected_id}'
            provider = 'Lever'
        elif host == 'jobs.smartrecruiters.com' and len(parts) >= 2:
            company = parts[0]
            m = re.match(r'(\d+)', parts[1])
            expected_id = m.group(1) if m else parts[1]
            endpoint = f'https://api.smartrecruiters.com/v1/companies/{company}/postings/{expected_id}'
            provider = 'SmartRecruiters'
        elif re.fullmatch(r'[a-z0-9-]+\.wd\d+\.myworkdayjobs\.com', host) and 'job' in parts:
            # Public Workday Candidate Experience exact-posting endpoint. A Workday
            # HTML shell, generic Apply text or missing posting never proves Live.
            site_i = next((i for i, part in enumerate(parts) if part.lower() == 'job'), -1)
            if site_i < 2 or site_i + 1 >= len(parts):
                return 'review', 'Workday URL lacks an exact site and job route'
            tenant = host.split('.')[0]
            site = parts[site_i - 1]
            route = '/'.join(quote(x, safe='-_.~') for x in parts[site_i + 1:])
            endpoint = f'https://{host}/wday/cxs/{tenant}/{quote(site, safe="-_.~")}/job/{route}'
            provider = 'Workday'
            expected_id = parts[-1].rsplit('_', 1)[-1]
        elif host == 'jobs.ashbyhq.com' and len(parts) >= 2:
            board, expected_id = parts[0], parts[1]
            endpoint = f'https://api.ashbyhq.com/posting-api/job-board/{board}'
            provider = 'Ashby'
        else:
            return None

        data = fetch_json(endpoint)
        if provider == 'Workday':
            info = data.get('jobPostingInfo') if isinstance(data, dict) else None
            if not isinstance(info, dict):
                return 'review', 'Workday exact posting API returned no jobPostingInfo'
            actual = str(info.get('jobReqId') or info.get('requisitionId') or '')
            # _R4043087-1 may be an URL suffix while the official jobReqId is R4043087.
            if not actual or not (expected_id.casefold() == actual.casefold()
                or expected_id.casefold().startswith(actual.casefold() + '-')):
                return 'review', 'Workday requisition ID did not match exact URL'
            if info.get('isClosed') is True or info.get('canApply') is False or info.get('isActive') is False:
                return 'expired', 'Workday exact posting API explicitly marks the requisition closed'
            can_apply = (info.get('canApply') is True or info.get('isActive') is True
                         or isinstance(info.get('applyUrl'), str) and bool(info.get('applyUrl')))
            if not can_apply:
                return 'review', 'Workday exact requisition found without explicit active application evidence'
            if not str(info.get('title') or '').strip():
                return 'review', 'Workday exact requisition lacks a job title'
            return 'active', 'Workday public exact posting inventory confirms requisition and active application'
        if provider == 'Ashby':
            jobs = data.get('jobs', []) if isinstance(data, dict) else []
            needle = expected_id.casefold()
            match = next((x for x in jobs if needle in str(x.get('jobUrl', '')).casefold() or needle in str(x.get('applyUrl', '')).casefold()), None)
            if match:
                return 'active', f'{provider} public posting inventory contains the exact published job'
            return 'review', f'{provider} board inventory did not contain the exact job; a missing ID without proven complete pagination is not closure evidence'

        if not isinstance(data, dict):
            return 'review', f'{provider} public posting inventory returned an unexpected response'
        actual = str(data.get('id') or data.get('uuid') or '')
        active_flag = data.get('active')
        if not actual:
            return 'review', f'{provider} inventory response omitted the exact requisition identifier'
        if expected_id and expected_id.casefold() not in {actual.casefold(), str(data.get('uuid') or '').casefold()}:
            return 'review', f'{provider} public posting inventory returned a different posting'
        if active_flag is False:
            return 'expired', f'{provider} public posting inventory marks the exact job inactive'
        title_or_text = str(data.get('title') or data.get('name') or data.get('text') or '').strip()
        if active_flag is not True and not title_or_text:
            return 'review', f'{provider} exact requisition lacks positive live posting evidence'
        return 'active', f'{provider} public posting inventory contains the exact published job'
    except HTTPError as exc:
        if exc.code in (404, 410):
            return 'review', f'{provider} exact posting API returned HTTP {exc.code}; confirm with an independent employer signal before expiry'
        return 'review', f'{provider} public posting inventory returned HTTP {exc.code}'
    except Exception as exc:
        return 'review', f'{provider} public posting inventory check was inconclusive ({type(exc).__name__})'

def structured_jobposting(body, job, now=None):
    """Read first-party JobPosting JSON-LD as an additional official signal."""
    now = now or datetime.now(timezone.utc)
    blocks = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', body, re.I | re.S)
    role = re.sub(r'\s+', ' ', str(job.get('role', ''))).strip().casefold()
    terms = [str(x).strip().casefold() for x in job.get('verificationTerms', []) if str(x).strip()]

    def walk(value):
        if isinstance(value, dict):
            yield value
            for v in value.values():
                yield from walk(v)
        elif isinstance(value, list):
            for v in value:
                yield from walk(v)

    for raw in blocks:
        try:
            payload = json.loads(raw)
        except Exception:
            continue
        for item in walk(payload):
            kinds = item.get('@type')
            kinds = kinds if isinstance(kinds, list) else [kinds]
            if 'JobPosting' not in kinds:
                continue
            blob = json.dumps(item, ensure_ascii=False).casefold()
            title = re.sub(r'\s+', ' ', str(item.get('title', ''))).strip().casefold()
            matched = bool((role and (role in blob or title in role or role in title)) or (terms and sum(t in blob for t in terms) >= min(2, len(terms))))
            if not matched:
                continue
            valid = item.get('validThrough')
            if valid:
                try:
                    dt = datetime.fromisoformat(str(valid).replace('Z', '+00:00'))
                    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                    if now >= dt:
                        return 'expired', 'Official JobPosting structured data validThrough deadline has passed'
                except Exception:
                    pass
            if item.get('directApply') is True or item.get('url') or item.get('identifier'):
                return 'review', 'Exact official JobPosting structured data exists, but a live application route is still required'
    return None

def normalize_role_heading(value):
    # ATS titles often use hyphen/en-dash/em-dash/slash interchangeably.
    # This is only used as supplemental visible-text matching on exact pages;
    # it is never independent evidence that an application is open.
    return re.sub(r'\s+', ' ', re.sub(r'[-\u2010-\u2015\u2212/]+', ' ', str(value).casefold())).strip()



def is_oracle_candidate_url(url):
    """Only exact public Oracle CX site requisition URLs qualify for browser fallback."""
    p = urlsplit(str(url))
    host = (p.hostname or '').lower()
    return bool(p.scheme == 'https' and re.fullmatch(r'[a-z0-9-]+\.fa\.oraclecloud\.com', host)
                and re.fullmatch(r'/hcmUI/CandidateExperience/(?:[a-z]{2}(?:-[A-Z]{2})?/)?sites/[A-Za-z0-9_]+/job/\d+/?', p.path))


def oracle_rendered_evidence(job, final_url, heading, text, enabled_apply):
    """Evaluate the rendered exact Oracle job page; no generic career page is Live."""
    expected = str(job.get('jobId') or urlsplit(str(job.get('apply') or '')).path.rstrip('/').rsplit('/', 1)[-1])
    if not is_oracle_candidate_url(job.get('apply')) or not expected.isdecimal():
        return 'review', 'Oracle Candidate Experience link is not a supported exact requisition URL'
    original = urlsplit(str(job.get('apply')))
    actual_url = urlsplit(str(final_url))
    if (actual_url.hostname or '').lower() != (original.hostname or '').lower() or actual_url.path.rstrip('/') != original.path.rstrip('/'):
        return 'review', 'Oracle browser navigation left the exact requisition page'
    if BLOCKED.search(text):
        return 'review', 'Oracle candidate page shows an access challenge'
    matched_id = re.search(r'\bJob\s+Identification\s*[:#]?\s*(\d{5,})\b',text,re.I)
    if not matched_id or matched_id.group(1) != expected:
        return 'review', 'Oracle rendered page did not show the matching Job Identification'
    title=normalize_role_heading(job.get('role') or '')
    rendered=normalize_role_heading(heading or '')
    if not title or title != rendered:
        return 'review', 'Oracle rendered requisition heading differs from stored job title'
    if re.search(r'\b(?:applications? closed|no longer accepting applications|this job is closed)\b', text,re.I):
        return 'review', 'Oracle rendered page contains conflicting closure text'
    if not enabled_apply:
        return 'review', 'Oracle exact requisition loaded without an enabled job Apply control'
    return 'active', 'Oracle rendered exact requisition confirms ID, role heading and enabled Apply control'


def oracle_browser_probe(job):
    """Optional real-browser check, no CAPTCHA/login bypass; fail closed without browser."""
    if os.getenv('HD_CAREERS_ENABLE_ORACLE_BROWSER') != '1':
        return None
    if not is_oracle_candidate_url(job.get('apply')):
        return None
    try:
        safe_url(job['apply'])
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
            try:
                page=browser.new_page(locale='en-US',viewport={'width':1280,'height':800})
                page.goto(job['apply'],wait_until='domcontentloaded',timeout=22000)
                page.wait_for_timeout(2800)
                page.wait_for_load_state('networkidle',timeout=4500)
            except Exception:
                # A timed-out networkidle isn't itself a failed application page;
                # only the rendered visible content below can establish Live.
                pass
            try:
                final_url=page.url
                text=page.locator('body').inner_text(timeout=7000)
                headings=page.locator('h1')
                heading=headings.first.inner_text(timeout=2000) if headings.count() else ''
                elements=page.locator('button, a, [role="button"]')
                enabled_apply=False
                for index in range(min(elements.count(),120)):
                    element=elements.nth(index)
                    if not element.is_visible() or not element.is_enabled():
                        continue
                    label=' '.join(element.inner_text(timeout=500).split())
                    aria=element.get_attribute('aria-label') or ''
                    if re.fullmatch(r'Apply(?:\s+Now)?',label,re.I) or re.fullmatch(r'Apply(?:\s+Now)?',aria,re.I):
                        if element.get_attribute('aria-disabled') != 'true':
                            enabled_apply=True
                            break
                return oracle_rendered_evidence(job,final_url,heading,text,enabled_apply)
            finally:
                browser.close()
    except Exception as exc:
        return 'review', 'Oracle browser verification inconclusive ('+type(exc).__name__+')'


def successfactors_exact_page(job,body,final_url,status=200):
    """Public SAP Recruiting Marketing exact posting, distinct page vs requisition IDs."""
    original=urlsplit(str(job.get('apply') or ''))
    resolved=urlsplit(str(final_url))
    if (original.hostname or '').lower() != 'jobs.sap.com' or not re.fullmatch(r'/job/[^/]+/\d+/?',original.path):
        return None
    if status != 200 or resolved.hostname != original.hostname or resolved.path.rstrip('/') != original.path.rstrip('/'):
        return 'review','SAP SuccessFactors exact career posting did not load at its original URL'
    parser=Visible()
    parser.feed(body)
    text=re.sub(r'\s+',' ',' '.join(parser.parts)).strip()
    if BLOCKED.search(text):
        return 'review','SAP SuccessFactors career posting shows an access challenge'
    expected=str(job.get('jobId') or '')
    match=re.search(r'\bRequisition\s+ID\s*[:#]?\s*(\d+)\b',text,re.I)
    if not expected or not match or match.group(1)!=expected:
        return 'review','SAP SuccessFactors exact requisition ID was not visible or mismatched'
    role=normalize_role_heading(job.get('role') or '')
    role_text=normalize_role_heading(text)
    if not role or role not in role_text:
        return 'review','SAP SuccessFactors visible exact role heading did not match'
    if re.search(r'\b(?:no longer accepting applications|job is closed|applications are closed)\b',text,re.I):
        return 'review','SAP SuccessFactors career page contains closure text'
    # Generic Apply text in headers is not evidence that this exact job accepts applications.
    apply_links=re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',body,re.I|re.S)
    valid_apply=any(
        re.search(r'\bApply\s+now\b',re.sub(r'<[^>]*>',' ',label),re.I)
        and not href.strip().lower().startswith(('javascript:','#','mailto:'))
        and urlsplit(urljoin(final_url,href)).hostname in {(urlsplit(final_url).hostname or '').lower(),
                                                             'career2.successfactors.eu','career5.successfactors.eu'}
        for href,label in apply_links
    )
    if not valid_apply:
        return 'review','SAP SuccessFactors posting has no clickable job-bound Apply now link'
    return 'active','SAP SuccessFactors official exact career page confirms requisition title and Apply now'

def classify(job, body, final_url, status=200):
    sf=successfactors_exact_page(job,body,final_url,status)
    if sf is not None: return sf
    if status in (404, 410): return 'review', f'HTTP {status} from automated request; exact job page requires browser verification before expiry'
    if status != 200: return 'review', f'HTTP {status}; availability unconfirmed'
    p = Visible(); p.feed(body)
    text = re.sub(r'\s+', ' ', ' '.join(p.parts)).strip()
    if BLOCKED.search(text): return 'review', 'Access challenge; availability unconfirmed'
    if final_url.rstrip('/') != job['apply'].rstrip('/'):
        return 'review', 'Redirected source requires browser/ATS verification'
    structured = structured_jobposting(body, job)
    # JSON-LD existence alone is not an active application signal. Check the visible
    # job page before falling back to Review; a passed official deadline stays final.
    if structured and structured[0] == 'expired':
        return structured
    closed = CLOSED.search(text)
    raw = re.sub(r'\s+', ' ', body).casefold()
    haystack = (text + ' ' + raw + ' ' + final_url).casefold()
    terms = [str(x).strip().casefold() for x in job.get('verificationTerms', []) if str(x).strip()]
    role = re.sub(r'\s+', ' ', job.get('role', '')).strip().casefold()
    matched = all(term in haystack for term in terms) if terms else bool(role and role in haystack)
    if not matched and not terms and urlsplit(final_url).hostname == 'jobs.lever.co':
        # Preserve exact-page and job-bound Apply requirements below. Only
        # compensate for typography variants in the VISIBLE job title, not JS.
        formatted_role = normalize_role_heading(role)
        formatted_text = normalize_role_heading(text)
        matched = bool(len(formatted_role) >= 15 and formatted_role in formatted_text)
    registration_control = bool(re.search(r'<form\\b|type=["\\\']submit["\\\']|\\bsubmit\\b', body, re.I))
    has_apply = bool(APPLY.search(text + ' ' + body) or (terms and registration_control))
    if closed and matched and has_apply:
        return 'review', f'Conflicting page evidence: closure text ({closed.group(0)}) and an exact role/application control are both present'
    if closed:
        return 'expired', closed.group(0)
    if matched and has_apply:
        if terms:
            return 'active', 'Verification terms and registration/submit control found on official URL'
        return 'active', 'Exact role and application call-to-action found on official URL'
    return structured or ('review', 'Official page loaded but role/application evidence was insufficient')

def check(job, now=None):
    now = now or datetime.now(timezone.utc)
    result = {'id': job.get('id'), 'url': job.get('apply'), 'checkedAt': now.isoformat()}
    try:
        if deadline_passed(job, now):
            state, reason = 'expired', 'Official closingAt deadline passed'
        else:
            safe_url(job['apply'])
            inventory = official_inventory_probe(job)
            if inventory and inventory[0] in {'active', 'expired'}:
                state, reason = inventory
                probes = []
            else:
                probes = []
            for label, user_agent in (() if (inventory and inventory[0] in {'active', 'expired'}) else (('browser', BROWSER_UA), ('bot', BOT_UA))):
                try:
                    req = Request(job['apply'], headers={
                        'User-Agent': user_agent,
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                    })
                    with build_opener(Redirects()).open(req, timeout=20) as res:
                        body = res.read(2_000_001)
                        if len(body) > 2_000_000: raise ValueError('Page exceeds inspection size limit')
                        probe_state, probe_reason = classify(job, body.decode('utf-8', errors='replace'), res.url, res.status)
                        probes.append((label, probe_state, probe_reason))
                except HTTPError as exc:
                    probes.append((label, 'review', f'HTTP {exc.code}; availability unconfirmed'))
                except Exception as exc:
                    probes.append((label, 'review', f'{type(exc).__name__}; availability unconfirmed'))

            browser = next((p for p in probes if p[0] == 'browser'), None)
            bot = next((p for p in probes if p[0] == 'bot'), None)

            if inventory and inventory[0] in {'active', 'expired'}:
                state, reason = inventory
            elif (is_oracle_candidate_url(job.get('apply')) and
                  (oracle_rendered := oracle_browser_probe(job)) is not None and
                  oracle_rendered[0] == 'active'):
                state, reason = oracle_rendered
            elif browser and browser[1] == 'active':
                state, reason = 'active', f'Browser-compatible official-page render is active ({browser[2]})'
                if bot and bot[1] == 'expired':
                    reason += f'; bot-only render reported closure ({bot[2]}) and was ignored'
            elif browser and bot and browser[1] == 'expired' and bot[1] == 'expired':
                if 'validThrough deadline has passed' in browser[2] and 'validThrough deadline has passed' in bot[2]:
                    state, reason = 'expired', 'Official JobPosting structured-data deadline has passed'
                else:
                    state, reason = 'review', f'Closure text appeared in both automated HTTP renders but requires ATS/rendered-browser confirmation before expiry ({browser[2]})'
            elif browser and bot and browser[1] != bot[1]:
                state, reason = 'review', f'Official page renders disagree: browser={browser[1]} ({browser[2]}); bot={bot[1]} ({bot[2]})'
            elif browser:
                state, reason = browser[1], browser[2]
            elif bot:
                state, reason = bot[1], bot[2]
            else:
                state, reason = 'review', 'No successful official-page probe'

            if state != 'active' and not (inventory and inventory[0] == 'expired') and not (state == 'expired' and 'deadline has passed' in reason) and manual_verification_fresh(job, now):
                automated_state, automated_reason = state, reason
                state = 'active'
                reason = f'Recent exact-job manual confirmation overrides inconclusive automated {automated_state} result within its verification window ({automated_reason}); verified at {job.get("manualLiveVerifiedAt") or job.get("browserVerifiedAt")}'
            elif state == 'expired' and not (inventory and inventory[0] == 'expired') and job.get('browserVerifiedAt'):
                state = 'review'
                reason = f'Automated closure conflicts with a previous manual browser verification ({job.get("manualLiveVerifiedAt") or job.get("browserVerifiedAt")}); re-review required before expiry'
    except HTTPError as exc:
        if manual_verification_fresh(job, now):
            state, reason = 'active', f'Recent exact-job manual confirmation overrides inconclusive automated HTTP {exc.code} result within its verification window; verified at {job.get("manualLiveVerifiedAt") or job.get("browserVerifiedAt")}'
        elif exc.code in (404, 410):
            state, reason = 'review', f'HTTP {exc.code} from automated request; exact job page requires browser verification before expiry'
        else:
            state, reason = 'review', f'HTTP {exc.code}; availability unconfirmed'
    except Exception as exc:
        if manual_verification_fresh(job, now):
            state, reason = 'active', f'Recent exact-job manual confirmation overrides the inconclusive automated result within its verification window; verified at {job.get("manualLiveVerifiedAt") or job.get("browserVerifiedAt")}'
        else:
            state, reason = 'review', f'Check incomplete ({type(exc).__name__})'
    return dict(result, state=state, reason=reason)


def has_high_confidence_live(job, result):
    """Qualification for owner shortlist: fresh, exact, positive employer evidence."""
    if result.get('state') != 'active':
        return False
    reason = str(result.get('reason') or '')
    host = (urlsplit(str(job.get('apply') or '')).hostname or '').lower()
    if '.myworkdayjobs.com' in host or '.myworkdaysite.com' in host:
        return reason.startswith('Workday public exact posting inventory confirms ')
    if is_oracle_candidate_url(job.get('apply')):
        return reason.startswith('Oracle rendered exact requisition confirms ID, role heading and enabled Apply control')
    if host == 'jobs.sap.com':
        return ('SAP SuccessFactors official exact career page confirms requisition title and Apply now' in reason)
    if 'manual confirmation overrides' in reason or 'override' in reason.lower():
        return False
    return (reason.startswith('Oracle rendered exact requisition confirms ID, role heading and enabled Apply control')
            or reason.startswith('SAP SuccessFactors official exact career page confirms requisition title and Apply now')
            or 'public posting inventory contains the exact published job' in reason
            or reason.startswith('Browser-compatible official-page render is active (Exact role and application call-to-action')
            or reason.startswith('Browser-compatible official-page render is active (Verification terms and registration/submit control'))


def expiry_decision(job, observed, previous=None, now=None):
    """Return final state plus auditable evidence; never close on a single ambiguous crawl."""
    now = now or datetime.now(timezone.utc)
    result = dict(observed)
    result['observedState'] = observed.get('state')
    if observed.get('state') != 'expired':
        return result
    reason = str(observed.get('reason') or '')
    definitive = (
        reason == 'Official closingAt deadline passed'
        or reason == 'Official JobPosting structured-data deadline has passed'
        or ('public posting inventory marks the exact job inactive' in reason)
        or reason == 'Workday exact posting API explicitly marks the requisition closed'
    )
    if definitive:
        result['expiryEvidence'] = 'authoritative'
        return result
    prior = previous or {}
    try:
        prior_at = datetime.fromisoformat(str(prior.get('checkedAt', '')).replace('Z', '+00:00'))
        if prior_at.tzinfo is None: prior_at = prior_at.replace(tzinfo=timezone.utc)
        separation = now - prior_at
        same = (prior.get('url') == job.get('apply') and
                prior.get('observedState', prior.get('state')) == 'expired' and
                timedelta(hours=6) <= separation <= timedelta(hours=36))
    except (TypeError, ValueError):
        same = False
    if same:
        result['expiryEvidence'] = 'independent-consecutive-scans'
        return result
    result['state'] = 'review'
    result['expiryEvidence'] = 'first_observation_unconfirmed'
    result['reason'] = f"Possible closure requires an independent second scan or owner review ({reason})"
    return result

def require_active(job):
    if job.get('status') != 'active': raise SystemExit('Publication blocked: job is not active')
    result = check(job)
    if result['state'] != 'active':
        raise SystemExit(f"Publication blocked for {job.get('company')} / {job.get('role')}: {result['reason']}")
    return result

def load_review_queue():
    try:
        data = json.loads(REVIEW_QUEUE.read_text())
        return data if isinstance(data, list) else []
    except Exception:
        return []

def review_key(job):
    return (str(job.get('apply', '')).strip().rstrip('/').lower(), str(job.get('company', '')).strip().lower(), str(job.get('role', '')).strip().lower())

def enqueue_reviews(jobs, results, source):
    result_by_id = {r.get('id'): r for r in results}
    pending = load_review_queue()
    by_key = {review_key(x.get('job', {})): x for x in pending if x.get('state') == 'review'}
    now = datetime.now(timezone.utc).isoformat()
    added = 0
    for offset, job in enumerate(jobs):
        result = result_by_id.get(job.get('id'))
        if not result or result.get('state') != 'review':
            continue
        key = review_key(job)
        existing = by_key.get(key)
        if existing:
            existing.update({
                'reason': result.get('reason', 'Availability unconfirmed'),
                'checkedAt': result.get('checkedAt', now),
                'job': job,
                'source': source,
            })
            continue
        review_id = int(time.time() * 1000) + offset
        item = {
            'reviewId': review_id,
            'kind': 'new_job',
            'state': 'review',
            'company': job.get('company', ''),
            'role': job.get('role', ''),
            'page': job.get('page', ''),
            'url': job.get('apply', ''),
            'reason': result.get('reason', 'Availability unconfirmed'),
            'checkedAt': result.get('checkedAt', now),
            'queuedAt': now,
            'source': source,
            'job': job,
        }
        pending.append(item)
        by_key[key] = item
        added += 1
    REVIEW_QUEUE.write_text(json.dumps(pending, ensure_ascii=False, indent=2) + '\n')
    return added

def prune_unverified_new_jobs(jobs, old_jobs, results):
    known_ids = {j.get('id') for j in old_jobs}
    rejected = {
        r.get('id') for r in results
        if r.get('id') not in known_ids and r.get('state') != 'active'
    }
    if not rejected:
        return jobs, [], []
    removed = [j for j in jobs if j.get('id') in rejected]
    return [j for j in jobs if j.get('id') not in rejected], sorted(rejected), removed

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--before', help='Verify new/reopened/changed-source jobs against this Git ref')
    parser.add_argument('--prune-unverified-new', action='store_true', help='Hold newly added unverified jobs for review and continue publishing verified jobs')
    args = parser.parse_args()
    path = ROOT / 'data/jobs.json'
    jobs = json.loads(path.read_text())
    selected = [j for j in jobs if j.get('status') == 'active']
    old = []
    known = {}
    if args.before:
        old = json.loads(subprocess.check_output(['git', 'show', f'{args.before}:data/jobs.json'], cwd=ROOT))
        known = {j['id']: j for j in old}
        selected = [j for j in selected if j['id'] not in known or any(j.get(k) != known[j['id']].get(k) for k in ('apply', 'status', 'role', 'company', 'closingAt', 'verificationTerms'))]
    status_path = ROOT / 'data' / 'availability-status.json'
    try:
        previous_status = json.loads(status_path.read_text()) if status_path.exists() else {}
    except (ValueError, OSError):
        previous_status = {}
    previous_by_id = {x.get('id'): x for x in previous_status.get('items', [])
                      if isinstance(x, dict)}
    results = []; changed = False; changed_expired = 0
    for job in selected:
        result = expiry_decision(job, check(job), previous_by_id.get(job.get('id'))) if args.write else check(job)
        results.append(result)
        print(f"{job['id']}: {result['state']} — {result['reason']}")
        if args.write and result['state'] == 'expired':
            job['status'] = 'expired'; job['availabilityCheck'] = result
            job['verifiedDate'] = datetime.now(timezone.utc).strftime('%d %b %Y'); changed = True; changed_expired += 1
    report = ROOT / 'availability-report.json'
    report.write_text(json.dumps(results, indent=2) + '\n')
    if args.write:
        by_id = {j.get('id'): j for j in jobs}
        checked_at = datetime.now(timezone.utc).isoformat()
        details = []
        for result in results:
            job = by_id.get(result.get('id'), {})
            details.append({
                'id': result.get('id'),
                'company': job.get('company', ''),
                'role': job.get('role', ''),
                'page': job.get('page', ''),
                'url': result.get('url', ''),
                'state': result.get('state', 'review'),
                'reason': result.get('reason', ''),
                'observedState': result.get('observedState', result.get('state')),
                'expiryEvidence': result.get('expiryEvidence', ''),
                'checkedAt': result.get('checkedAt', checked_at),
            })
        states = [x.get('state') for x in details]
        summary = {
            'checkedAt': checked_at,
            'checked': len(details),
            'active': states.count('active'),
            'expired': states.count('expired'),
            'review': states.count('review'),
            'changedExpired': changed_expired,
            'items': details,
        }
        status_path = ROOT / 'data' / 'availability-status.json'
        status_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    if args.before and args.prune_unverified_new:
        jobs, pruned, removed = prune_unverified_new_jobs(jobs, old, results)
        if removed:
            queued = enqueue_reviews(removed, results, 'repository_publish')
            path.write_text(json.dumps(jobs, ensure_ascii=False, indent=2) + '\n')
            print(f'Held {queued} new job(s) in Needs Review. Removed IDs: ' + ', '.join(str(x) for x in pruned))
        blocking = [r for r in results if r['state'] != 'active' and r.get('id') not in set(pruned)]
        if blocking:
            raise SystemExit('Verification failed for an existing/changed job; publishing stopped')
    elif args.before and any(r['state'] != 'active' for r in results):
        raise SystemExit('New job verification failed; publishing stopped')
    if changed:
        path.write_text(json.dumps(jobs, ensure_ascii=False, indent=2) + '\n')

if __name__ == '__main__': main()
