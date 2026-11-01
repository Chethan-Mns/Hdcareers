"""Offline and deterministic tests for official-ATS network pacing."""
import io
import sys
import unittest
from pathlib import Path
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from ats_http_client import ATSClient, NoRedirect, permitted


class FakeResponse:
    def __init__(self, url, body=b'{"jobs":[]}'):
        self.url, self.body = url, body
    def geturl(self):
        return self.url
    def read(self, maxbytes):
        return self.body
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False


class FakeClock:
    def __init__(self):
        self.t = 10.0
        self.delays = []
    def now(self):
        return self.t
    def sleep(self, seconds):
        self.delays.append(seconds)
        self.t += seconds


class FakeOpener:
    def __init__(self, steps):
        self.steps = list(steps)
        self.calls = []
    def open(self, req, timeout=15):
        self.calls.append((req.full_url, req.get_method(), timeout))
        next_step = self.steps.pop(0)
        if isinstance(next_step, Exception):
            raise next_step
        return FakeResponse(req.full_url, next_step)


class ATSHTTPTests(unittest.TestCase):
    def test_allowlist_blocks_non_https_bad_hosts_and_private_resources(self):
        for url in ("http://api.lever.co/v0/postings", "https://example.com/",
                    "https://localhost/", "https://127.0.0.1/private",
                    "https://api.lever.co@localhost/private",
                    "https://api.lever.co:8080/v0/postings"):
            self.assertFalse(permitted(url), url)
        self.assertTrue(permitted("https://api.lever.co/v0/postings/acme"))
        self.assertTrue(permitted("https://example.wd3.myworkdayjobs.com/wday/cxs/x/y/jobs"))

    def test_host_pacing_and_post_are_enforced(self):
        clock = FakeClock()
        opener = FakeOpener([b'{"jobs":[]}', b'{"jobs":[]}', b'{"jobs":[]}'])
        client = ATSClient(clock=clock.now, sleep=clock.sleep,
                           opener=opener, min_interval=1)
        url = "https://api.lever.co/v0/postings/acme"
        self.assertEqual(client.fetch_json(url)["jobs"], [])
        self.assertEqual(client.fetch_json(url)["jobs"], [])
        self.assertEqual(clock.delays, [1])
        self.assertEqual(client.fetch_json(
            "https://example.wd3.myworkdayjobs.com/wday/cxs/example/a/jobs",
            {"offset": 0})["jobs"], [])
        self.assertEqual(opener.calls[2][1], "POST")

    def test_http_429_retry_after_host_hold_and_success(self):
        clock = FakeClock()
        problem = HTTPError("https://api.lever.co/v0/postings/acme", 429,
                            "Too many requests", {"Retry-After": "3"}, None)
        opener = FakeOpener([problem, b'{"ok":true}'])
        client = ATSClient(clock=clock.now, sleep=clock.sleep, opener=opener,
                           min_interval=0.1, attempts=3)
        self.assertTrue(client.fetch_json("https://api.lever.co/v0/postings/acme")["ok"])
        self.assertEqual(clock.delays, [3.0])
        self.assertEqual(len(opener.calls), 2)

    def test_exhausted_429_fails_not_silently_success(self):
        clock = FakeClock()
        errors = [HTTPError("https://api.lever.co/a", 429, "refused", {"Retry-After": "0"}, None)
                  for _ in range(2)]
        client = ATSClient(clock=clock.now, sleep=clock.sleep,
                           opener=FakeOpener(errors), attempts=2)
        with self.assertRaises(HTTPError):
            client.fetch_json("https://api.lever.co/a")

    def test_nonretryable_errors_never_retried(self):
        err = HTTPError("https://api.lever.co/a", 404, "gone", {}, None)
        opener = FakeOpener([err])
        client = ATSClient(opener=opener, attempts=3)
        with self.assertRaises(HTTPError):
            client.fetch_json("https://api.lever.co/a")
        self.assertEqual(len(opener.calls), 1)

    def test_rejects_oversized_or_malformed_responses(self):
        client = ATSClient(opener=FakeOpener([b'{"too_big":"abcdefghij"}']),
                           max_bytes=10)
        with self.assertRaises(ValueError):
            client.fetch_json("https://api.ashbyhq.com/posting-api/job-board/acme")

    def test_redirects_fail_closed(self):
        self.assertRaises(ValueError, NoRedirect().redirect_request,
                          None, None, 302, "Moved", {},
                          "https://other-company.example/private")


if __name__ == "__main__":
    unittest.main()
