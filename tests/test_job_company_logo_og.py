"""Company-logo-only Open Graph previews for HD Careers job pages.

No image generation, no media posting, and no changes to existing message text.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

import generate

ROOT = Path(__file__).resolve().parents[1]


class CompanyLogoLinkPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jobs = json.loads((ROOT / "data/jobs.json").read_text(encoding="utf-8"))

    def job(self, company):
        for j in self.jobs:
            if j.get("company") == company:
                return j
        raise AssertionError("Missing known employer: " + company)

    def test_synopsys_uses_original_logo_not_generated_card(self):
        job = self.job("Synopsys")
        image, mime, alt = generate._company_logo_preview_source(job)
        self.assertTrue(image.startswith("https://hdcareers.in/assets/"))
        self.assertTrue(image.endswith(".png"))
        self.assertIn("synopsys", image)
        self.assertIn("Synopsys", alt)
        self.assertEqual(mime, "image/png")
        self.assertNotIn("job-previews/", image)
        body = generate.render_job_page(job, self.jobs)
        self.assertIn('<meta property="og:image" content="' + image + '">', body)
        self.assertNotIn("synopsys-cad-design-support-apprenticeship-v2.png", body)
        self.assertEqual(body.count('property="og:image"'), 1)
        self.assertIn('name="twitter:image" content="' + image + '"', body)

    def test_known_approved_company_logos(self):
        for name in ("Chaosology Technologies", "Synopsys", "Brillio"):
            with self.subTest(company=name):
                job = self.job(name)
                src, mime, alt = generate._company_logo_preview_source(job)
                self.assertIn("hdcareers.in/assets/", src)
                self.assertNotIn("job-previews/", src)
                self.assertTrue(mime.startswith("image/"))
                self.assertIn(name, alt)
                page = generate.render_job_page(job, self.jobs)
                self.assertIn('property="og:image" content="' + src + '"', page)
                self.assertIn('property="og:image:alt" content="' + name + ' logo"', page)

    def test_unverified_or_nonraster_logo_uses_safe_fallback(self):
        dummy = {"company": "Completely Unknown Placeholder Employer",
                 "page": "jobs/unknown-placeholder.html",
                 "logoPath": "../.env",
                 "logoSourceDomain": "",
                 "domain": "unknown.invalid"}
        src, mime, alt = generate._company_logo_preview_source(dummy)
        self.assertEqual(src, "https://hdcareers.in/assets/hd-careers-logo.png")
        self.assertEqual(mime, "image/png")
        self.assertEqual(alt, "HD Careers logo")

    def test_every_job_has_one_unique_open_graph_image_and_absolute_url(self):
        for job in self.jobs:
            with self.subTest(job=job.get("page")):
                body = generate.render_job_page(job, self.jobs)
                self.assertEqual(body.count('property="og:image"'), 1)
                self.assertEqual(body.count('property="og:image:secure_url"'), 1)
                src, mime, alt = generate._company_logo_preview_source(job)
                self.assertIn('property="og:image" content="' + src + '"', body)
                self.assertIn('property="og:image:type" content="' + mime + '"', body)
                self.assertNotIn('<!-- One-post premium WhatsApp trial', body)

    def test_original_whapi_message_format_and_queue_are_untouched(self):
        relay = (ROOT / "scripts/whapi_channel_relay.py").read_text()
        self.assertIn('shared.fmt(job)', relay)
        self.assertIn('"/messages/text"', relay)
        self.assertIn('verify_admin()', relay)
        self.assertIn('provider_accepted', relay)


if __name__ == "__main__":
    unittest.main()
