import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import generate


def sample(**overrides):
    job = {
        "id": 1,
        "page": "jobs/example.html",
        "company": "Example",
        "role": "Data Engineer",
        "apply": "https://careers.example.com/jobs/123",
        "status": "active",
        "date": "Not Specified",
        "verifiedDate": "13 Oct 2026",
        "loc": "Bengaluru",
        "desc": "Data engineering role",
        "elig": "Bachelor degree",
        "resp": ["Build ETL"],
        "skills": ["Python"],
    }
    job.update(overrides)
    return job


class Phase1SafetyTests(unittest.TestCase):
    def test_missing_employer_date_does_not_invent_posting_date(self):
        self.assertEqual(generate.job_posting_schema(sample(), "https://hdcareers.in/jobs/example.html"), "")

    def test_employer_date_can_generate_structured_data(self):
        html = generate.job_posting_schema(sample(date="12 Oct 2026"), "https://hdcareers.in/jobs/example.html")
        self.assertIn('"datePosted": "2026-10-12"', html)

    def test_expired_listing_excludes_jobposting(self):
        self.assertEqual(generate.job_posting_schema(sample(status="expired", date="12 Oct 2026"), "https://hdcareers.in/jobs/example.html"), "")

    def test_uncertain_listing_excludes_jobposting(self):
        self.assertEqual(generate.job_posting_schema(sample(date="12 Oct 2026", _verification_pending=True), "https://hdcareers.in/jobs/example.html"), "")

    def annotate(self, jobs, report):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "availability-status.json"
            path.write_text(json.dumps({"items": [report]}), encoding="utf-8")
            with patch.object(generate, "AVAILABILITY_FILE", path):
                generate.annotate_latest_availability(jobs)

    def test_review_remains_listed_but_not_verified(self):
        job = sample()
        self.annotate([job], {
            "id": 1, "url": job["apply"], "state": "review",
            "checkedAt": "2026-10-13T09:47:56+00:00",
        })
        self.assertEqual(job["status"], "active")
        self.assertTrue(job["_verification_pending"])

    def test_newer_exact_manual_live_proof_overrides_old_review(self):
        job = sample(manualLiveVerifiedAt="2026-10-13T10:00:00Z", manualLiveVerifiedUrl="https://careers.example.com/jobs/123")
        self.annotate([job], {
            "id": 1, "url": job["apply"], "state": "review",
            "checkedAt": "2026-10-13T09:47:56+00:00",
        })
        self.assertNotIn("_verification_pending", job)

    def test_old_or_wrong_url_manual_proof_does_not_override_review(self):
        job = sample(manualLiveVerifiedAt="2026-10-13T10:00:00Z", manualLiveVerifiedUrl="https://careers.example.com/other")
        self.annotate([job], {
            "id": 1, "url": job["apply"], "state": "review",
            "checkedAt": "2026-10-13T09:47:56+00:00",
        })
        self.assertTrue(job["_verification_pending"])

    def test_stale_report_for_different_url_is_ignored(self):
        job = sample()
        self.annotate([job], {
            "id": 1, "url": "https://careers.example.com/jobs/old", "state": "review",
            "checkedAt": "2026-10-13T09:47:56+00:00",
        })
        self.assertNotIn("_verification_pending", job)

    def test_active_result_does_not_become_pending(self):
        job = sample()
        self.annotate([job], {
            "id": 1, "url": job["apply"], "state": "active",
            "checkedAt": "2026-10-13T09:47:56+00:00",
        })
        self.assertNotIn("_verification_pending", job)

    def test_generator_template_marks_pending_and_preserves_apply_link(self):
        job = sample(_verification_pending=True, date="12 Oct 2026")
        job.update({
            "page": "jobs/example.html", "domain": "example.com",
            "salary": "Not Disclosed", "logo": ["EX", "#123456"],
            "roleTag": "Data Engineer", "locationFilter": "Bengaluru",
            "batch": "Not Specified", "cat": "it", "expType": "fresher",
            "expYears": "0 years", "sourceName": "Example Careers",
            "who": "Graduates", "workMode": "Onsite",
        })
        output = generate.render_job_page(job, [job])
        self.assertIn("Verification pending", output)
        self.assertNotIn("<strong>Verified active:</strong>", output)
        self.assertNotIn('"@type": "JobPosting"', output)
        self.assertIn("https://careers.example.com/jobs/123", output)


if __name__ == "__main__":
    unittest.main()
