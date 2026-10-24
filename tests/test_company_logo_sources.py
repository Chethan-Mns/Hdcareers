"""Protect curated HD Careers logos and ban shared ATS icons site-wide."""
import json
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PROVIDERS=("greenhouse.io","myworkdayjobs.com","ashbyhq.com","lever.co",
           "smartrecruiters.com","workable.com","icims.com","taleo.net",
           "oraclecloud.com","successfactors.com","jobvite.com","teamtailor.com")


class CompanyLogoRules(unittest.TestCase):
    def setUp(self):
        self.approved=json.loads((ROOT/"data/approved-company-logos.json").read_text())
        self.jobs=json.loads((ROOT/"data/jobs.json").read_text())
        self.resolver=(ROOT/"scripts/resolve_company_logos.py").read_text()
        self.generator=(ROOT/"generate.py").read_text()
        self.home=(ROOT/"index.html").read_text()

    def test_owner_uploads_are_valid_branded_assets(self):
        from PIL import Image
        from xml.etree import ElementTree as ET
        for name in ("Amazon","Google","Microsoft"):
            path=ROOT/self.approved[name]
            self.assertTrue(path.is_file(),f"Missing approved {name} artwork")
            if path.suffix==".svg":
                root=ET.parse(path).getroot()
                self.assertTrue(root.tag.endswith("svg"))
                self.assertGreater(len(list(root)),2)
            else:
                with Image.open(path) as img:
                    img.verify()
                with Image.open(path) as img:
                    self.assertGreaterEqual(img.width,128)
                    self.assertGreaterEqual(img.height,128)

    def test_every_approved_asset_preserved(self):
        for name,path in self.approved.items():
            self.assertTrue((ROOT/path).is_file(),f"{name} logo missing: {path}")

    def test_provider_domains_are_rejected(self):
        from scripts.resolve_company_logos import is_generic
        for host in PROVIDERS:
            self.assertTrue(is_generic("jobs."+host),host)
        self.assertFalse(is_generic("glance.com"))
        self.assertFalse(is_generic("66degrees.com"))
        self.assertFalse(is_generic("instawork.com"))

    def test_homepage_never_selects_ats_favicon(self):
        func=self.home.split("function companyLogo(",1)[1].split("\nfunction parseJobDate(",1)[0]
        for unsafe in ("companyInternetLogos(", "careerFavicon(", "careerDomainFavicon(", "google.com/s2", "duckduckgo.com"):
            self.assertNotIn(unsafe,func)
        self.assertIn("APPROVED_COMPANY_LOGOS",func)
        self.assertIn("logoFallback",func)

    def test_detail_pages_use_same_logo_contract(self):
        part=self.generator.split("def logo_candidates(",1)[1].split("\ndef logo_onerror(",1)[0]
        for unsafe in ("career_favicon_url(", "career_domain_favicon(", "logo_sources(", "google.com/s2", "duckduckgo.com"):
            self.assertNotIn(unsafe,part)
        self.assertIn("APPROVED_COMPANY_LOGOS",part)

    def test_requested_fit_adjustments_are_non_destructive(self):
        names=("arm","rubrik","new street technologies","wayfair")
        for n in names:
            self.assertIn(n,self.home.split("function companyLogo(",1)[1])
            self.assertIn(n,self.generator.split("def logo_zoom_style(",1)[1])
        self.assertNotIn("old.unlink()",self.resolver)

    def test_company_ats_examples_are_configured(self):
        domains=json.loads((ROOT/"data/company-logo-domains.json").read_text())
        for name in ("Glance","Instawork","66degrees"):
            self.assertIn(name,domains)
            self.assertNotIn("greenhouse.io",domains[name])

    def test_all_registered_job_logos_are_local_existing_assets(self):
        for job in self.jobs:
            logo = str(job.get("logoPath") or "").strip()
            if not logo:
                continue  # Reviewed missing logos intentionally display the initials fallback.
            with self.subTest(company=job["company"], page=job["page"]):
                self.assertTrue(logo.startswith("assets/"), logo)
                self.assertNotIn("..", Path(logo).parts)
                self.assertTrue((ROOT/logo).is_file(), f"Broken image path: {logo}")

    def test_cached_company_logos_never_use_shared_ats_branding(self):
        from urllib.parse import urlparse
        manifest=json.loads((ROOT/"data/company-logos.json").read_text())
        for company, entry in manifest.items():
            with self.subTest(company=company):
                path = entry.get("localPath", "")
                self.assertTrue(path.startswith("assets/"), path)
                self.assertTrue((ROOT/path).is_file(), f"Missing logo asset: {company} {path}")
                source_host=(urlparse(entry.get("sourceUrl") or "").hostname or "").lower()
                if source_host == "c.smartrecruiters.com":
                    self.assertEqual(entry.get("verificationStatus"), "employer-managed-careers-asset")
                    self.assertEqual(entry.get("sourceType"), "employer-uploaded careers brand logo")
                else:
                    self.assertFalse(any(source_host == h or source_host.endswith("."+h)
                        for h in PROVIDERS), f"Shared ATS logo was cached: {company}, {source_host}")


if __name__=="__main__":
    unittest.main()
