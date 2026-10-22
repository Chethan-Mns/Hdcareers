"""Regression coverage for the source-generated shared job hero.

The header + hero may change, but all original job-body sections, content,
status safeguards, resume parser hooks, CTA destinations and SEO remain intact.
"""
import json
import unittest
from pathlib import Path

import generate


ROOT = Path(__file__).resolve().parents[1]


class SharedHeroTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jobs = json.loads((ROOT / "data/jobs.json").read_text(encoding="utf-8"))

    def test_all_job_pages_receive_new_hero_and_original_body(self):
        self.assertGreaterEqual(len(self.jobs), 150)
        for job in self.jobs:
            with self.subTest(page=job["page"]):
                body = generate.render_job_page(job, self.jobs)
                self.assertIn('class="hdj3-hero"', body)
                self.assertIn('href="../assets/job-hero.css"', body)
                self.assertIn("Resume Readiness Check", body)
                self.assertIn("Job Overview</h2>", body)
                self.assertIn(">Eligibility</h2>", body)
                self.assertIn("Skills Mentioned</h2>", body)
                self.assertIn("Key Responsibilities</h2>", body)
                self.assertIn("Who Should Apply?</h2>", body)
                self.assertIn('id="resumeMatch"', body)
                self.assertEqual(body.count('id="resumeFile"'), 1)
                self.assertEqual(body.count('id="resumeMatch"'), 1)
                self.assertIn("function runSampleMatch()", body)
                self.assertIn("async function readResumeFile(file)", body)
                self.assertIn("https://hdcareers.in/" + job["page"], body)
                self.assertIn("Useful Before You Apply", body)
                self.assertIn("Need a correction?", body)
                self.assertLess(body.index('class="hdj3-hero"'), body.index('id="resumeMatch"'))
                self.assertIn(job["company"], body)

    def test_status_does_not_get_upgraded_by_hero(self):
        for job in self.jobs:
            body = generate.render_job_page(job, self.jobs)
            hero = body.split('<section class="hdj3-hero"', 1)[1].split('</section>', 1)[0]
            if job["status"] == "expired":
                self.assertIn("ARCHIVED JOB", hero)
                self.assertNotIn('data-hd-track="job_apply_click"', hero)
                self.assertIn("Browse Active Jobs", hero)
            elif job.get("_verification_pending"):
                self.assertIn("RECHECK AVAILABILITY", hero)
                self.assertIn("Availability unconfirmed", hero)
            else:
                self.assertIn("VERIFIED SNAPSHOT", hero)
                self.assertIn(job["apply"].replace("&", "&amp;"), hero)

    def test_same_resume_assessment_engine_and_source_data(self):
        job = next(j for j in self.jobs if j["company"] == "EY" and j["status"] == "active")
        body = generate.render_job_page(job, self.jobs)
        self.assertIn('src="/assets/resume-assessment.js"', body)
        self.assertIn('src="/assets/resume-keywords.js"', body)
        self.assertIn('onclick="document.getElementById(\'resumeFile\').click()"', body)
        self.assertIn('onclick="runSampleMatch()"', body)
        self.assertEqual(body.count('class="hdj3-card"'), 1)


if __name__ == "__main__":
    unittest.main()
