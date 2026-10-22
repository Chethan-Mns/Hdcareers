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


    def test_job_hero_uses_identical_content_gutters_as_original_body(self):
        css = (ROOT / "assets/job-hero.css").read_text(encoding="utf-8")
        self.assertIn(".hdj3-shell{max-width:72rem;margin:0 auto;padding:28px 1rem 35px}", css)
        self.assertIn(".hdj3-shell{padding-inline:1rem}", css)
        self.assertNotIn(".hdj3-shell{max-width:1280px", css)
        for job in self.jobs:
            with self.subTest(page=job["page"]):
                body = generate.render_job_page(job, self.jobs)
                self.assertIn('<section class="max-w-6xl mx-auto px-4 py-7', body)
                self.assertIn('<div class="hdj3-shell">', body)

    def test_low_end_mobile_job_content_never_waits_for_scroll_animation(self):
        css = (ROOT / "assets/job-hero.css").read_text(encoding="utf-8")
        # Both independent scroll animation systems must be overridden by a
        # visible-by-default stylesheet scoped to the generated job pages.
        self.assertIn(".reveal-on-scroll,.hd-motion{", css)
        for rule in ("opacity:1!important;", "visibility:visible!important;",
                     "transform:none!important;", "will-change:auto!important;"):
            self.assertIn(rule, css)
        self.assertIn(".hdj3-hero::before,.hdj3-hero::after{display:none}", css)
        for job in self.jobs:
            with self.subTest(page=job["page"]):
                body = generate.render_job_page(job, self.jobs)
                self.assertIn('href="../assets/job-hero.css"', body)
                self.assertIn("Job Overview</h2>", body)
                self.assertIn("Skills Mentioned</h2>", body)
                self.assertIn("Key Responsibilities</h2>", body)
                self.assertIn('id="resumeMatch"', body)
                self.assertIn('src="/assets/resume-assessment.js"', body)


if __name__ == "__main__":
    unittest.main()
