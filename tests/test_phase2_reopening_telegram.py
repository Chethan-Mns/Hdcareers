import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_job_availability import (
    official_inventory_probe, check, choose_reopening_candidates, manual_verification_fresh
)
import publish_approved_telegram as telegram


class Reply:
    status = 200
    def __init__(self, url, body):
        self.url = url
        self.body = body.encode()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, *_):
        return self.body


class Opener:
    def __init__(self, url, body=None, error=None):
        self.url = url
        self.body = body
        self.error = error
    def open(self, *args, **kwargs):
        if self.error:
            raise self.error
        return Reply(self.url, self.body)


class ReopeningAndConflicts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jobs = {x["id"]: x for x in json.loads((ROOT / "data/jobs.json").read_text())}

    def test_nielseniq_exact_inactive_ats_is_review_not_expired(self):
        job = self.jobs[82]
        self.assertEqual(job["status"], "expired")
        with patch("check_job_availability.fetch_json", return_value={"id": "744000152930140", "active": False}):
            self.assertEqual(official_inventory_probe(job)[0], "review")

    def test_nielseniq_inactive_ats_conflicts_with_exact_live_apply_page(self):
        job = dict(self.jobs[82], status="active")
        body = "<h1>Associate Software Engineer</h1><p>Up to 6 months experience; Java; final year</p><a href='/apply'>Apply now</a>"
        with patch("check_job_availability.safe_url"), patch("check_job_availability.fetch_json", return_value={"id": "744000152930140", "active": False}), patch("check_job_availability.build_opener", return_value=Opener(job["apply"], body)):
            result = check(job)
        self.assertEqual(result["state"], "review")
        self.assertIn("Conflicting official evidence", result["reason"])

    def test_ats_without_exact_identifier_never_confirms_live(self):
        job = self.jobs[82]
        with patch("check_job_availability.fetch_json", return_value={"active": True}):
            self.assertEqual(official_inventory_probe(job)[0], "review")

    def test_deloitte_usi_404_does_not_confirm_expiry_or_reopening(self):
        job = self.jobs[75]
        error = HTTPError(job["apply"], 404, "Not found", {}, None)
        with patch("check_job_availability.safe_url"), patch("check_job_availability.build_opener", return_value=Opener(job["apply"], error=error)):
            result = check(job)
        self.assertEqual(result["state"], "review")
        self.assertEqual(job["status"], "expired")

    def test_expired_without_owner_closure_requires_both_api_and_public_application(self):
        job = dict(self.jobs[82], status="expired")
        body = "<h1>Associate Software Engineer</h1><p>Up to 6 months experience; Java; final year</p><button>Apply now</button>"
        with patch("check_job_availability.safe_url"), patch("check_job_availability.official_inventory_probe", return_value=("active", "Exact ATS active")), patch("check_job_availability.build_opener", return_value=Opener(job["apply"],body)):
            result = check(job)
        self.assertEqual(result["state"], "active")
        self.assertIn("Reopening confirmed:", result["reason"])

    def test_exact_api_without_live_public_page_cannot_reopen(self):
        job = dict(self.jobs[82], status="expired")
        with patch("check_job_availability.safe_url"), patch("check_job_availability.official_inventory_probe", return_value=("active", "ATS exact job")), patch("check_job_availability.build_opener", return_value=Opener(job["apply"], "<h1>Associate Software Engineer</h1>")):
            result = check(job)
        self.assertEqual(result["state"], "review")
        self.assertIn("Potential reopening", result["reason"])

    def test_owner_closed_job_must_not_auto_reopen(self):
        job = self.jobs[104]
        self.assertEqual(job["status"], "expired")
        self.assertTrue(job.get("manualClosedVerifiedAt"))
        body = "<h1>Senior Software Engineer</h1>Apply now"
        with patch("check_job_availability.safe_url"), patch("check_job_availability.official_inventory_probe", return_value=("active", "Exact ATS active")), patch("check_job_availability.build_opener", return_value=Opener(job["apply"],body)):
            result = check(job)
        self.assertEqual(result["state"], "review")
        self.assertIn("Owner-verified closure", result["reason"])

    def test_bounded_expired_rotation_keeps_owner_closed_jobs_eligible_for_audit(self):
        jobs = [{"id": i,"status": "expired"} for i in range(24)]
        chosen = choose_reopening_candidates(jobs, datetime(2026, 10, 15, tzinfo=timezone.utc), limit=6)
        self.assertEqual(len(chosen), 6)
        self.assertEqual(len({x["id"] for x in chosen}), 6)
        self.assertTrue(all(x["status"] == "expired" for x in chosen))


class SafeTelegramRetry(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.manifest = Path(self.temp.name) / "approved.json"
        self.ledger = Path(self.temp.name) / "ledger.json"
        self.job = {"id": 1111, "page": "jobs/test-new-opening.html", "status": "active", "company": "Test", "role": "Engineer", "apply": "https://careers.example.com/job"}
        self.manifest.write_text(json.dumps({"approved": True, "batchId": "one-new-job", "pages": [self.job["page"]]}))
        patches=[
            patch.object(telegram,"MANIFEST",self.manifest),
            patch.object(telegram,"LEDGER",self.ledger),
            patch.object(telegram,"load_current_jobs",return_value=[self.job]),
            patch.object(telegram,"check",return_value={"state":"active","reason":"Exact ATS active"}),
            patch.object(telegram,"wait_for_exact_page",return_value=True),
            patch.object(telegram,"message_for",return_value="test message"),
            patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN":"not-real","TELEGRAM_CHANNEL_ID":"@fake_test_channel","JOB_PAGES":""}),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def receipt(self):
        return json.loads(self.ledger.read_text())

    def test_successful_send_is_never_duplicated(self):
        with patch.object(telegram,"send_telegram",return_value=493) as send:
            telegram.publish()
            telegram.publish()
        self.assertEqual(send.call_count,1)
        self.assertEqual(next(iter(self.receipt().values()))["messageId"],493)

    def test_http_429_acknowledged_rejection_is_safe_retry(self):
        with patch.object(telegram,"send_telegram",side_effect=[RuntimeError("Telegram HTTP 429: retry later"),494]) as send:
            with self.assertRaisesRegex(RuntimeError, "429"):
                telegram.publish()
            self.assertEqual(next(iter(self.receipt().values()))["status"],"failed")
            telegram.publish()
        self.assertEqual(send.call_count,2)
        self.assertEqual(next(iter(self.receipt().values()))["status"],"delivered")

    def test_http_503_remains_uncertain_and_blocks_retry(self):
        with patch.object(telegram,"send_telegram",side_effect=RuntimeError("Telegram HTTP 503: server error")) as send:
            with self.assertRaises(RuntimeError):
                telegram.publish()
            self.assertEqual(next(iter(self.receipt().values()))["status"],"uncertain")
            with self.assertRaisesRegex(SystemExit,"uncertain"):
                telegram.publish()
        self.assertEqual(send.call_count,1)

    def test_timeout_remains_uncertain_and_blocks_retry(self):
        with patch.object(telegram,"send_telegram",side_effect=TimeoutError("deadline exceeded")) as send:
            with self.assertRaises(TimeoutError):
                telegram.publish()
            self.assertEqual(next(iter(self.receipt().values()))["status"],"uncertain")
            with self.assertRaises(SystemExit):
                telegram.publish()
        self.assertEqual(send.call_count,1)

    def test_missing_message_id_blocks_retry(self):
        with patch.object(telegram,"send_telegram",return_value=None) as send:
            with self.assertRaisesRegex(RuntimeError,"no valid message ID"):
                telegram.publish()
            with self.assertRaises(SystemExit):
                telegram.publish()
        self.assertEqual(send.call_count,1)
        self.assertEqual(next(iter(self.receipt().values()))["status"],"uncertain")

    def test_expired_or_unverified_job_does_not_send(self):
        self.job["status"] = "expired"
        with patch.object(telegram,"send_telegram") as send:
            with self.assertRaisesRegex(SystemExit,"not active"):
                telegram.publish()
        send.assert_not_called()


if __name__=="__main__":
    unittest.main()
