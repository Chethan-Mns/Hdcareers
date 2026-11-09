"""Safety regressions for automatic job closure."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_job_availability import guard_automatic_expiry

class ExpiryGuardTests(unittest.TestCase):
    def setUp(self):
        self.job={"id":42,"apply":"https://example.org/careers/42"}
        self.now=datetime(2026, 11, 9, 10, 0, tzinfo=timezone.utc)

    def test_first_closure_waits(self):
        c={}
        result, closed=guard_automatic_expiry(self.job,{"state":"expired","reason":"Greenhouse inventory inactive"},c,self.now)
        self.assertFalse(closed)
        self.assertEqual(result["state"],"review")
        self.assertIn("42",c)

    def test_repeat_closure_expires_after_interval(self):
        c={}
        e={"state":"expired","reason":"Greenhouse inventory inactive"}
        guard_automatic_expiry(self.job,e,c,self.now)
        r,closed=guard_automatic_expiry(self.job,e,c,self.now+timedelta(hours=12))
        self.assertTrue(closed)
        self.assertEqual(r["state"],"expired")
        self.assertNotIn("42",c)

    def test_error_resets_closure_candidate(self):
        c={}
        e={"state":"expired","reason":"Greenhouse inventory inactive"}
        guard_automatic_expiry(self.job,e,c,self.now)
        guard_automatic_expiry(self.job,{"state":"review","reason":"HTTP 403"},c,self.now+timedelta(minutes=40))
        _,closed=guard_automatic_expiry(self.job,e,c,self.now+timedelta(hours=12))
        self.assertFalse(closed)

    def test_deadline_expires_immediately(self):
        r,c=guard_automatic_expiry(self.job,{"state":"expired","reason":"Official closingAt deadline passed"},{},self.now)
        self.assertTrue(c)
        self.assertEqual(r["state"],"expired")

    def test_new_url_never_inherits_expiry(self):
        c={"42":{"firstSeenAt":(self.now-timedelta(hours=12)).isoformat(),"apply":"https://example.org/old","reason":"closed"}}
        _,closed=guard_automatic_expiry(self.job,{"state":"expired","reason":"new closed"},c,self.now)
        self.assertFalse(closed)

if __name__=="__main__":
    unittest.main()
