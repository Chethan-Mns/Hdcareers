"""Contract tests for confirmed-live publication and confirmed-closed expiry."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))
from check_job_availability import classify, official_inventory_probe, review_history
from admin_publish import confirmed_live_for_publish
import generate

NOW = datetime(2026, 10, 13, 14, 0, tzinfo=timezone.utc)
SOURCE = "https://job-boards.greenhouse.io/acme/jobs/12345"


class ConfirmedOnlyTests(unittest.TestCase):
    def test_ten_manual_results_remain_immutable_fixture(self):
        fixture = json.loads((ROOT / "tests/fixtures/owner_manual_verification_20261013.json").read_text())
        rows = fixture["cases"]
        self.assertEqual(len(rows), 10)
        self.assertEqual(sum(x["userVerdict"] == "live" for x in rows), 6)
        self.assertEqual(sum(x["userVerdict"] == "expired" for x in rows), 4)
        self.assertEqual({x["id"] for x in rows if x["recordedVerdict"] == "review"}, {108, 109, 104})
        self.assertEqual({x["id"] for x in rows if x["recordedVerdict"] == "expired"}, {118, 76, 75})

    def test_ats_missing_or_wrong_identity_cannot_be_confirmed_active(self):
        job = {"id": 1, "apply": SOURCE}
        for response in ({"active": True}, {"active": False}, {"title": "Data Engineer"},
                         {"id": "999", "active": True}, {"id": "999", "active": False}, []):
            with self.subTest(response=response), patch("check_job_availability.fetch_json", return_value=response):
                self.assertEqual(official_inventory_probe(job)[0], "review")

    def test_matching_exact_id_can_confirm_live_or_closed(self):
        job = {"id": 1, "apply": SOURCE}
        for flag, verdict in ((True, "active"), (False, "expired")):
            with patch("check_job_availability.fetch_json", return_value={"id": 12345, "active": flag, "title": "Data Engineer"}):
                self.assertEqual(official_inventory_probe(job)[0], verdict)

    def test_matching_id_without_title_or_active_evidence_is_not_live(self):
        job = {"id": 1, "role": "Data Engineer", "apply": SOURCE}
        rows = [
            {"id": 12345},
            {"id": 12345, "active": True},
            {"id": 12345, "title": "Different Role", "active": True},
            {"id": 12345, "title": "Data Engineer"},
        ]
        for response in rows:
            with self.subTest(response=response), patch("check_job_availability.fetch_json", return_value=response):
                self.assertEqual(official_inventory_probe(job)[0], "review")

    def test_ashby_partial_id_substring_is_not_live(self):
        job = {"id": 1, "apply": "https://jobs.ashbyhq.com/acme/abc-123"}
        response = {"jobs": [{"jobUrl": "https://jobs.ashbyhq.com/acme/abc-1234"}]}
        with patch("check_job_availability.fetch_json", return_value=response):
            self.assertEqual(official_inventory_probe(job)[0], "review")

    def test_missing_jobposting_title_cannot_expire_some_other_job(self):
        job = {"id": 1, "role": "Data Engineer", "apply": SOURCE}
        body = '<script type="application/ld+json">{"@type":"JobPosting","identifier":"Data Engineer","validThrough":"2020-01-01T00:00:00Z"}</script>'
        self.assertEqual(classify(job, body, SOURCE)[0], "review")

    def test_new_listing_requires_matching_url_current_source_positive(self):
        job = {"id": 139, "apply": SOURCE}
        good = {"id": 139, "url": SOURCE, "checkedAt": NOW.isoformat(), "state": "active",
                "reason": "Greenhouse public posting inventory contains the exact published job"}
        self.assertTrue(confirmed_live_for_publish(job, good, NOW))
        for changes in ({"state": "review"}, {"state": "expired"},
                        {"url": "https://other.example.com/jobs/12345"}, {"id": 999},
                        {"checkedAt": (NOW - timedelta(hours=3)).isoformat()},
                        {"reason": "Unknown positive signal"}, {"checkedAt": "invalid"}):
            with self.subTest(changes=changes):
                self.assertFalse(confirmed_live_for_publish(job, dict(good, **changes), NOW))

    def test_recent_owner_live_proof_can_publish_but_stale_cannot(self):
        job = {"id": 108, "apply": "https://careers.example.com/jobs/108",
               "manualLiveVerifiedAt": (NOW - timedelta(hours=3)).isoformat(),
               "manualLiveVerifiedUrl": "https://careers.example.com/jobs/108"}
        result = {"id": 108, "url": job["apply"], "checkedAt": NOW.isoformat(), "state": "active",
                  "reason": "Recent exact-job manual confirmation overrides inconclusive automated review result"}
        self.assertTrue(confirmed_live_for_publish(job, result, NOW))
        self.assertFalse(confirmed_live_for_publish(dict(job, manualLiveVerifiedAt=(NOW - timedelta(hours=26)).isoformat()), result, NOW))
        self.assertFalse(confirmed_live_for_publish(dict(job, manualLiveVerifiedUrl="https://other.example.com"), result, NOW))

    def test_review_history_requires_same_url_and_consecutive_checks(self):
        first = {"id": 109, "url": SOURCE, "state": "review", "checkedAt": (NOW - timedelta(days=3)).isoformat()}
        n, started = review_history({}, first)
        self.assertEqual(n, 1)
        self.assertEqual(started, first["checkedAt"])
        previous = dict(first, consecutiveReviewCount=n, firstReviewAt=started)
        self.assertEqual(review_history(previous, dict(first, checkedAt=NOW.isoformat())), (2, started))
        self.assertEqual(review_history(previous, dict(first, url="https://other.example.com")), (1, first["checkedAt"]))
        self.assertEqual(review_history(previous, dict(first, state="active")), (0, None))

    def annotate(self, job, item):
        with tempfile.TemporaryDirectory() as tmp:
            filename = Path(tmp) / "availability-status.json"
            filename.write_text(json.dumps({"items": [item]}))
            with patch.object(generate, "AVAILABILITY_FILE", filename):
                generate.annotate_latest_availability([job])

    def test_two_uncertain_checks_over_72h_hold_from_latest_without_expiring(self):
        job = {"id": 109, "status": "active", "apply": SOURCE}
        item = {"id": 109, "state": "review", "url": SOURCE,
                "checkedAt": NOW.isoformat(), "consecutiveReviewCount": 2,
                "firstReviewAt": (NOW - timedelta(hours=75)).isoformat()}
        self.annotate(job, item)
        self.assertTrue(job["_verification_pending"])
        self.assertTrue(job["_hold_from_latest"])
        self.assertFalse(generate.visible_in_latest(job))
        self.assertEqual(job["status"], "active")

    def test_fresh_review_or_recent_owner_confirmation_keeps_listing_visible(self):
        first = {"id": 109, "state": "review", "url": SOURCE,
                 "checkedAt": NOW.isoformat(), "consecutiveReviewCount": 1,
                 "firstReviewAt": (NOW - timedelta(hours=75)).isoformat()}
        job = {"id": 109, "status": "active", "apply": SOURCE}
        self.annotate(job, first)
        self.assertTrue(generate.visible_in_latest(job))
        job2 = {"id": 109, "status": "active", "apply": SOURCE,
                "manualLiveVerifiedAt": (NOW - timedelta(hours=2)).isoformat(),
                "manualLiveVerifiedUrl": SOURCE}
        self.annotate(job2, dict(first, consecutiveReviewCount=3))
        self.assertTrue(generate.visible_in_latest(job2))

    def test_owner_review_api_records_url_bound_live_and_closure(self):
        text = (ROOT / "api/admin/review.js").read_text()
        self.assertIn("job.manualLiveVerifiedAt=now;", text)
        self.assertIn("job.manualLiveVerifiedUrl=job.apply;", text)
        self.assertIn("job.manualClosedVerifiedAt=now;", text)
        self.assertIn("job.manualClosedVerifiedUrl=job.apply;", text)


if __name__ == "__main__":
    unittest.main()
