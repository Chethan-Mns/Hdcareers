"""Conservative official-page checks shared by monitoring and publishing."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
import ipaddress
import json
from pathlib import Path
import re
import socket
import subprocess
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
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
    raw = job.get('browserVerifiedAt')
    if not raw: return False
    try:
        dt = datetime.fromisoformat(str(raw).replace('Z', '+00:00'))
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return timedelta(0) <= now - dt <= timedelta(hours=24)
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
        elif host == 'jobs.ashbyhq.com' and len(parts) >= 2:
            board, expected_id = parts[0], parts[1]
            endpoint = f'https://api.ashbyhq.com/posting-api/job-board/{board}'
            provider = 'Ashby'
        else:
            return None

        data = fetch_json(endpoint)
        if provider == 'Ashby':
            jobs = data.get('jobs', []) if isinstance(data, dict) else []
            needle = expected_id.casefold()
            match = next((x for x in jobs if needle in str(x.get('jobUrl', '')).casefold() or needle in str(x.get('applyUrl', '')).casefold()), None)
            if match:
                return 'active', f'{provider} public posting inventory contains the exact published job'
            return 'expired', f'{provider} public posting inventory no longer contains the exact job'

        if not isinstance(data, dict):
            return 'review', f'{provider} public posting inventory returned an unexpected response'
        actual = str(data.get('id') or data.get('uuid') or '')
        active_flag = data.get('active')
        if expected_id and actual and expected_id.casefold() not in {actual.casefold(), str(data.get('uuid') or '').casefold()}:
            return 'review', f'{provider} public posting inventory returned a different posting'
        if active_flag is False:
            return 'expired', f'{provider} public posting inventory marks the exact job inactive'
        return 'active', f'{provider} public posting inventory contains the exact published job'
    except HTTPError as exc:
        if exc.code in (404, 410):
            return 'expired', f'{provider} public posting inventory returned HTTP {exc.code} for the exact posting'
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

def classify(job, body, final_url, status=200):
    if status in (404, 410): return 'review', f'HTTP {status} from automated request; exact job page requires browser verification before expiry'
    if status != 200: return 'review', f'HTTP {status}; availability unconfirmed'
    p = Visible(); p.feed(body)
    text = re.sub(r'\s+', ' ', ' '.join(p.parts)).strip()
    if BLOCKED.search(text): return 'review', 'Access challenge; availability unconfirmed'
    if final_url.rstrip('/') != job['apply'].rstrip('/'):
        return 'review', 'Redirected source requires browser/ATS verification'
    structured = structured_jobposting(body, job)
    if structured:
        return structured
    closed = CLOSED.search(text)
    raw = re.sub(r'\s+', ' ', body).casefold()
    haystack = (text + ' ' + raw + ' ' + final_url).casefold()
    terms = [str(x).strip().casefold() for x in job.get('verificationTerms', []) if str(x).strip()]
    role = re.sub(r'\s+', ' ', job.get('role', '')).strip().casefold()
    matched = all(term in haystack for term in terms) if terms else bool(role and role in haystack)
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
    return 'review', 'Official page loaded but role/application evidence was insufficient'

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

            if state != 'active' and not (inventory and inventory[0] == 'expired') and manual_verification_fresh(job, now):
                automated_state, automated_reason = state, reason
                state = 'active'
                reason = f'Fresh manual browser verification overrides automated {automated_state} result for 24 hours ({automated_reason}); verified at {job["browserVerifiedAt"]}'
            elif state == 'expired' and not (inventory and inventory[0] == 'expired') and job.get('browserVerifiedAt'):
                state = 'review'
                reason = f'Automated closure conflicts with a previous manual browser verification ({job["browserVerifiedAt"]}); re-review required before expiry'
    except HTTPError as exc:
        if manual_verification_fresh(job, now):
            state, reason = 'active', f'Fresh manual browser verification overrides automated HTTP {exc.code} result for 24 hours; verified at {job["browserVerifiedAt"]}'
        elif exc.code in (404, 410):
            state, reason = 'review', f'HTTP {exc.code} from automated request; exact job page requires browser verification before expiry'
        else:
            state, reason = 'review', f'HTTP {exc.code}; availability unconfirmed'
    except Exception as exc:
        if manual_verification_fresh(job, now):
            state, reason = 'active', f'Fresh manual browser verification overrides the inconclusive automated result for 24 hours; verified at {job["browserVerifiedAt"]}'
        else:
            state, reason = 'review', f'Check incomplete ({type(exc).__name__})'
    return dict(result, state=state, reason=reason)

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
    results = []; changed = False
    for job in selected:
        result = check(job); results.append(result)
        print(f"{job['id']}: {result['state']} — {result['reason']}")
        if args.write and result['state'] == 'expired':
            job['status'] = 'expired'; job['availabilityCheck'] = result
            job['verifiedDate'] = datetime.now(timezone.utc).strftime('%d %b %Y'); changed = True
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
                'checkedAt': result.get('checkedAt', checked_at),
            })
        states = [x.get('state') for x in details]
        summary = {
            'checkedAt': checked_at,
            'checked': len(details),
            'active': states.count('active'),
            'expired': states.count('expired'),
            'review': states.count('review'),
            'changedExpired': states.count('expired'),
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
