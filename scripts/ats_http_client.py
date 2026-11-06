#!/usr/bin/env python3
"""Conservative, rate-limited official ATS HTTP transport.

No scraping proxies, no login, no redirects, and no requests to arbitrary hosts.
Rate-limit per host; respect Retry-After. API errors never imply job expiry.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

API_HOSTS = {
    "boards-api.greenhouse.io", "api.lever.co", "api.eu.lever.co",
    "api.ashbyhq.com", "api.smartrecruiters.com",
}
WORKDAY_HOST = re.compile(r"^[a-z0-9-]+\.wd\d+\.myworkdayjobs\.com$")
RETRYABLE = {429, 500, 502, 503, 504}


def permitted(url):
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    return (
        parsed.scheme == "https" and parsed.port in (None, 443)
        and parsed.username is None and parsed.password is None
        and (host in API_HOSTS or bool(WORKDAY_HOST.fullmatch(host)))
    )


class NoRedirect(HTTPRedirectHandler):
    """Never follow an ATS redirect to a login wall or an uncontrolled host."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("ATS API redirects are not trusted")


class ATSClient:
    def __init__(self, min_interval=0.5, attempts=3, timeout=15,
                 clock=None, sleep=None, opener=None, max_bytes=3_000_000):
        if min_interval < 0 or not 1 <= attempts <= 4 or timeout <= 0:
            raise ValueError("Invalid ATS transport limits")
        self.min_interval = min_interval
        self.attempts = attempts
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.clock = clock or time.monotonic
        self.sleep = sleep or time.sleep
        self.opener = opener or build_opener(NoRedirect())
        self.next_request_at = {}

    @staticmethod
    def retry_after(error):
        raw = error.headers.get("Retry-After", "") if error.headers else ""
        if not raw:
            return None
        try:
            return max(0.0, min(60.0, float(raw)))
        except (ValueError, TypeError):
            try:
                dt = parsedate_to_datetime(raw)
                if dt.tzinfo is None:
                    return None
                return max(0.0, min(60.0, (dt - datetime.now(timezone.utc)).total_seconds()))
            except (ValueError, TypeError, OverflowError, IndexError):
                return None

    def fetch_json(self, url, body=None):
        if not permitted(url):
            raise ValueError("Non-allowlisted official ATS API endpoint")
        host = urlsplit(url).hostname.lower()
        headers = {
            "Accept": "application/json",
            "User-Agent": "HDCareersATSResearch/1.0 (read-only official boards)",
        }
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        for attempt in range(self.attempts):
            now = self.clock()
            hold = self.next_request_at.get(host, 0.0)
            if hold > now:
                self.sleep(hold - now)
            self.next_request_at[host] = self.clock() + self.min_interval
            req = Request(url, data=data, headers=headers,
                          method="POST" if data is not None else "GET")
            try:
                with self.opener.open(req, timeout=self.timeout) as response:
                    # Defense in depth in case a custom opener unexpectedly redirects.
                    if not permitted(response.geturl()):
                        raise ValueError("ATS API redirected outside allowed hosts")
                    raw = response.read(self.max_bytes + 1)
                    if len(raw) > self.max_bytes:
                        raise ValueError("ATS API response exceeded size budget")
                    return json.loads(raw.decode("utf-8"))
            except HTTPError as exc:
                if exc.code not in RETRYABLE or attempt + 1 >= self.attempts:
                    raise
                pause = self.retry_after(exc)
                if pause is None:
                    pause = min(8.0, 1.0 * (2 ** attempt))
                self.next_request_at[host] = max(
                    self.next_request_at[host], self.clock() + pause)
        raise RuntimeError("Unreachable ATS retry loop")


DEFAULT_CLIENT = ATSClient()


def fetch_json(url, body=None, *, timeout=None):
    # Existing discovery and test call sites remain compatible.
    if timeout is None:
        return DEFAULT_CLIENT.fetch_json(url, body)
    temporary = ATSClient(
        min_interval=DEFAULT_CLIENT.min_interval,
        attempts=DEFAULT_CLIENT.attempts,
        timeout=timeout,
        clock=DEFAULT_CLIENT.clock, sleep=DEFAULT_CLIENT.sleep,
        opener=DEFAULT_CLIENT.opener,
    )
    return temporary.fetch_json(url, body)
