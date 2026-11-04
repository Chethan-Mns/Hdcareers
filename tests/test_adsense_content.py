"""Content quality regressions for the AdSense remediation (not an approval predictor)."""
import json
import unittest
from pathlib import Path

import generate

ROOT = Path(__file__).resolve().parents[1]


class ContentQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jobs = json.loads((ROOT / "data/jobs.json").read_text(encoding="utf-8"))

    def test_clear_student_and_graduate_positions_are_not_experienced_only(self):
        role_ids = {
            314, 317, 322, 308, 310, 312, 299, 301, 290, 294, 295,
            296, 278, 280, 271, 263, 266, 255, 256, 250, 251, 252, 197
        }
        found = {j["id"]: j for j in self.jobs if j["id"] in role_ids}
        self.assertEqual(set(found), role_ids)
        for job in found.values():
            with self.subTest(company=job["company"], role=job["role"]):
                self.assertEqual(job["expType"], "fresher")

    def test_unsubstantiated_generated_filler_is_omitted(self):
        sample = [j for j in self.jobs if j.get("status") == "active"][:40]
        self.assertGreaterEqual(len(sample), 10)
        for job in sample:
            with self.subTest(page=job["page"]):
                rendered = generate.render_job_page(job, self.jobs)
                self.assertNotIn("Job FAQ</h2>", rendered)
                self.assertNotIn("Skills to Demonstrate</h2>", rendered)
                self.assertNotIn("No other active listings from this company", rendered)
                self.assertIn('rel="canonical"', rendered)
                if "review the official requirements and apply if" in str(job.get("who", "")).lower():
                    self.assertNotIn("Who Should Apply?</h2>", rendered)
                if job.get("jobId"):
                    self.assertIn("Employer and requisition details", rendered)

    def test_editorial_insights_are_real_data_and_crawlable(self):
        page = generate.render_insights_page(self.jobs)
        weekly = generate.render_insights_page(self.jobs, detailed=True)
        for markup in [page, weekly]:
            self.assertIn("What the current listings actually show", markup)
            self.assertIn("listing counts", markup)
            self.assertNotIn("{{EDITORIAL_INSIGHTS}}", markup)
            self.assertNotIn("{{PREFIX}}", markup)
            self.assertNotIn('href="{PREFIX}', markup)
        self.assertIn('href="../editorial-policy.html"', weekly)
        self.assertIn('href="editorial-policy.html"', page)

    def test_original_guides_contain_real_exercises_and_next_steps(self):
        guide_markers = {
            "resume-tips-for-freshers.html": "Worked example: turn a student project into evidence",
            "online-assessment-preparation.html": "Three practice exercises with explanations",
            "job-scam-red-flags.html": "Scenario: an interview invitation arrives on WhatsApp",
        }
        for name, marker in guide_markers.items():
            with self.subTest(guide=name):
                content = (ROOT / "resources" / name).read_text(encoding="utf-8")
                self.assertGreater(len(content), 7000)
                self.assertIn(marker, content)
                self.assertIn('rel="canonical"', content)
                self.assertIn("</article>", content)

    def test_expired_jobs_cannot_claim_active_schema(self):
        for job in self.jobs:
            if job.get("status") != "active":
                with self.subTest(page=job["page"]):
                    markup = generate.render_job_page(job, self.jobs)
                    self.assertIn('content="noindex,follow"', markup)
                    self.assertNotIn('"@type": "JobPosting"', markup)


if __name__ == "__main__":
    unittest.main()
