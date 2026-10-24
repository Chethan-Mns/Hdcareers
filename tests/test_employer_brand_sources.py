"""Tests for ATS-independent corporate logo sourcing and publication safety."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import employer_brand_sources as brand
import resolve_company_logos as logos


class EmployerBrandSourceTests(unittest.TestCase):
    def test_header_logo_beats_ats_favicons(self):
        html = """
        <html><head><link rel="icon" href="/favicon.ico"></head>
        <body><header><img alt="Onehouse logo" src="/assets/onehouse.svg"></header>
        <img alt="Partner company logo" src="/other-company.svg"></body></html>
        """
        results = brand.official_logo_candidates(html, "https://www.onehouse.ai/", "Onehouse")
        self.assertEqual(results[0][1], "https://www.onehouse.ai/assets/onehouse.svg")
        self.assertNotIn("other-company.svg", str(results))

    def test_matching_jsonld_logo_precedes_favicon(self):
        html = """<link rel="icon" href="/favicon.ico">
        <script type="application/ld+json">
        {"@context":"https://schema.org","@graph":[
         {"@type":"Organization","name":"Vodafone","logo":{"url":"https://www.vodafone.com/logo.svg"}},
         {"@type":"Organization","name":"Other","logo":"https://other.com/logo.svg"}]}
        </script>"""
        results = brand.official_logo_candidates(html, "https://www.vodafone.com/", "Vodafone")
        self.assertEqual(results[0][1], "https://www.vodafone.com/logo.svg")
        self.assertNotIn("other.com", str(results))

    def test_detects_ats_hosts_and_forms(self):
        for host in ["jobs.lever.co", "fa.ocs.oraclecloud.com", "jobs.myworkdayjobs.com",
                     "airtable.com", "docs.google.com", "forms.office.com", "forms.gle",
                     "job-boards.greenhouse.io", "formstack.com", "tally.so"]:
            with self.subTest(host=host):
                self.assertTrue(logos.is_generic(host))
        for host in ["barclays.com", "vodafone.com", "onehouse.ai", "eclerx.com"]:
            self.assertFalse(logos.is_generic(host))

    def test_configured_employer_domain_wins_over_oracle_and_airtable(self):
        config = json.loads((ROOT / "data/company-logo-domains.json").read_text())
        for name, apply, wanted in [
            ("Onehouse", "https://jobs.lever.co/Onehouse/abc", "onehouse.ai"),
            ("eClerx", "https://fa.ocs.oraclecloud.com/hcmUI/job/84612", "eclerx.com"),
            ("AlgoUniversity", "https://airtable.com/appxxx/form", "algouniversity.com"),
            ("Standard Chartered", "https://jobs.standardchartered.com/job/58757", "sc.com"),
            ("Vodafone", "https://jobs.vodafone.com/careers/job/123", "vodafone.com"),
            ("Barclays", "https://search.jobs.barclays/job/123", "barclays.com"),
        ]:
            with self.subTest(name=name):
                self.assertEqual(logos.official_domain({"company": name, "apply": apply}, config), wanted)

    def test_unknown_ats_employer_from_explicit_corporate_home_link(self):
        html = """<a href="https://onehouse.ai/">Onehouse Home Page</a>
                    <a href="https://lever.co">Lever Home Page</a>"""
        with patch.object(logos, "fetch", return_value=(html.encode(), "text/html", "https://jobs.lever.co/Onehouse/x")):
            domain = logos.official_domain(
                {"company": "Onehouse", "apply": "https://jobs.lever.co/Onehouse/x"}, {})
        self.assertEqual(domain, "onehouse.ai")

    def test_ats_does_not_become_domain_when_employer_unknown(self):
        with patch.object(logos, "fetch", return_value=(b"<html>Form received</html>", "text/html", "https://airtable.com/x")):
            self.assertEqual(logos.official_domain({"company": "Mystery", "apply": "https://airtable.com/x"}, {}), "")

    def test_embedded_metadata_requires_matching_employer(self):
        html = """<script type="application/ld+json">
             {"@type":"JobPosting","hiringOrganization":{"@type":"Organization",
             "name":"Onehouse","url":"https://onehouse.ai/"}}</script>"""
        self.assertEqual(
            brand.employer_website_candidates(html, "https://jobs.lever.co/Onehouse/x", "Onehouse"),
            ["https://onehouse.ai/"]
        )
        self.assertEqual(
            brand.employer_website_candidates(html, "https://jobs.lever.co/Onehouse/x", "OtherCo"), []
        )

    def test_svg_sanitizer_rejects_executable_content(self):
        for svg in [
            b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"><path d="M1 2"/></svg>',
            b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
            b'<svg xmlns="http://www.w3.org/2000/svg"><image href="https://evil.com/pic"/></svg>',
            b'<svg xmlns="http://www.w3.org/2000/svg"><foreignObject>hi</foreignObject></svg>',
            b'<!DOCTYPE svg><svg xmlns="http://www.w3.org/2000/svg"/>',
        ]:
            with self.subTest(svg=svg[:50]):
                self.assertIsNone(brand.safe_svg_bytes(svg))
        self.assertIsNotNone(brand.safe_svg_bytes(
            b'<svg xmlns="http://www.w3.org/2000/svg"><path fill="#0055aa" d="M0 0H10V10Z"/></svg>'
        ))

    def test_logo_sources_prefer_corporate_header_and_not_google_favicon_proxy(self):
        html = '<header><img alt="Standard Chartered logo" src="/static/logo.svg"></header><link rel="icon" href="/favicon.ico">'
        with patch.object(logos, "fetch", return_value=(html.encode(), "text/html", "https://www.sc.com/")):
            candidates = logos.candidate_urls("sc.com", company="Standard Chartered")
        self.assertEqual(candidates[0][1], "https://www.sc.com/static/logo.svg")
        self.assertFalse(any("google.com/s2" in row[1] for row in candidates))

    def test_smartrecruiters_company_uploaded_brand_can_be_used_safely(self):
        page = b"""<html><body>
          <img alt="Caribou Media Pvt Ltd logo"
               src="https://c.smartrecruiters.com/sr-company-logo-prod-aws-dc5/employer/huge"/>
          <img alt="SmartRecruiters logo"
               src="https://c.smartrecruiters.com/provider-logo.svg"/>
        </body></html>"""
        source = "https://jobs.smartrecruiters.com/CaribouMediaPvtLtd/84098168-php-developer"
        sample = {"company": "Caribou Media", "apply": source}
        with patch.object(logos, "fetch", return_value=(page, "text/html", source)):
            with patch.object(logos, "evaluate_remote_candidate", return_value=(900, b"sample", ".png", "https://c.smartrecruiters.com/sr-company-logo-prod-aws-dc5/employer/huge", "employer-uploaded careers brand logo", (120, 120))) as evaluate:
                result = logos.employer_uploaded_careers_logo(sample)
        self.assertIsNotNone(result)
        self.assertTrue(evaluate.call_args.kwargs["allow_employer_ats_brand"])
        self.assertIn("sr-company-logo-prod-aws", evaluate.call_args.args[1])

    def test_no_ats_employer_brand_fallback_without_exact_named_image(self):
        source = "https://jobs.smartrecruiters.com/Company/123"
        page = b'<img alt="SmartRecruiters logo" src="https://c.smartrecruiters.com/provider.svg">'
        with patch.object(logos, "fetch", return_value=(page, "text/html", source)):
            with patch.object(logos, "evaluate_remote_candidate") as evaluate:
                result = logos.employer_uploaded_careers_logo({"company": "Caribou Media", "apply": source})
        self.assertIsNone(result)
        evaluate.assert_not_called()

    def test_non_smartrecruiters_form_never_supplies_brand_logo(self):
        with patch.object(logos, "fetch") as fetcher:
            self.assertIsNone(logos.employer_uploaded_careers_logo({
                "company": "Company", "apply": "https://airtable.com/abc"
            }))
        fetcher.assert_not_called()

    def test_official_48px_icons_allowed_when_higher_resolution_unavailable(self):
        self.assertIsNotNone(logos.raster_score(64, 64, 200))
        self.assertIsNone(logos.raster_score(32, 32, 200))

    def test_accepts_wide_wordmark_when_source_is_branded_logo(self):
        self.assertIsNotNone(logos.raster_score(600, 110, 800, wordmark=True))
        self.assertIsNone(logos.raster_score(600, 110, 300, wordmark=False))


    def test_vetted_employer_careers_asset_accepts_only_exact_employer_upload(self):
        source = {
            "Caribou Media": {
                "sourceUrl": "https://c.smartrecruiters.com/sr-company-logo-prod-aws-dc5/55a62c83e4b0dda8e68ef188/huge?r=1",
                "evidenceUrl": "https://jobs.smartrecruiters.com/CaribouMediaPvtLtd/743999677660729-business-analyst-it-experience-",
                "sourceType": "employer-uploaded careers brand logo"
            }
        }
        with patch.object(logos, "evaluate_remote_candidate", return_value=(850, b"PNG", ".png", source["Caribou Media"]["sourceUrl"], "employer-uploaded careers brand logo", (128, 128))) as evaluate:
            self.assertIsNotNone(logos.vetted_employer_careers_logo("Caribou Media", source))
            self.assertTrue(evaluate.call_args.kwargs["allow_employer_ats_brand"])
            self.assertIsNone(logos.vetted_employer_careers_logo("Other Co", source))

    def test_vetted_careers_asset_rejects_provider_icon_or_untrusted_host(self):
        example = {"evidenceUrl": "https://jobs.smartrecruiters.com/Example/123",
                   "sourceType": "employer-uploaded careers brand logo"}
        with patch.object(logos, "evaluate_remote_candidate") as evaluate:
            for invalid in ("https://c.smartrecruiters.com/favicon.ico",
                            "https://attacker.example/sr-company-logo-prod-aws-dc5/55a62c83e4b0dda8e68ef188/huge",
                            "https://c.smartrecruiters.com/sr-company-logo-prod-aws-dc5/not-an-id/huge"):
                self.assertIsNone(logos.vetted_employer_careers_logo("Example", {"Example": {**example, "sourceUrl": invalid}}))
            evaluate.assert_not_called()

    def test_vetted_careers_assets_have_reviewable_provenance(self):
        entries = json.loads((ROOT / "data/company-logo-vetted-careers-assets.json").read_text(encoding="utf-8"))
        for company, asset in entries.items():
            with self.subTest(company=company):
                self.assertTrue(asset["evidenceUrl"].startswith("https://jobs.smartrecruiters.com/"))
                self.assertEqual(asset["sourceType"], "employer-uploaded careers brand logo")
                self.assertTrue(asset["sourceUrl"].startswith("https://c.smartrecruiters.com/sr-company-logo-prod-aws-dc5/"))


if __name__ == "__main__":
    unittest.main()
