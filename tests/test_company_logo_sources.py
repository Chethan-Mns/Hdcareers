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

    def test_owner_requested_zoom_only_for_caribou_and_dataflair(self):
        css=(ROOT/"assets/job-hero.css").read_text(encoding="utf-8")
        homepage=self.home.split("<style>",1)[1].split("</style>",1)[0]
        for key in ("company-icons/caribou-media-","company-icons/dataflair-web-services-pvt-ltd-"):
            self.assertIn(key,homepage)
            self.assertIn(key,css)
        self.assertIn("scale(1.25)!important",homepage)
        self.assertIn("scale(1.25)!important",css)
        # Prevent the change from affecting other employer icons or their fallback logic.
        self.assertNotIn(".company-logo img{transform:scale(1.25)",homepage)
        self.assertNotIn(".hdj3-logo img{transform:scale(1.25)",css)

    def test_new_owner_logo_replacements_are_registered(self):
        for company in ("LinuxBean Solution","Blueberry Labs","Mactores","Portcast",
                        "MongoDB","ION Group","Turner & Townsend"):
            path=self.approved.get(company,"")
            with self.subTest(company=company):
                self.assertTrue(path.startswith("assets/company-owner/"),path)
                self.assertTrue((ROOT/path).is_file(),path)
                self.assertEqual(Path(path).suffix,".webp")

    def test_logo_refresh_is_visible_for_four_requested_employers(self):
        from PIL import Image
        expected={
            "MongoDB": "mongodb-leaf-v2-20261024.webp",
            "SuperApp": "superapp-chat-v2-20261024.webp",
            "Blueberry Labs": "blueberry-labs-compact-v2-20261024.webp",
        }
        for company,name in expected.items():
            with self.subTest(company=company):
                asset=self.approved.get(company,"")
                self.assertEqual(Path(asset).name,name)
                with Image.open(ROOT/asset) as img:
                    self.assertEqual(img.size,(384,384))
                    self.assertEqual(img.format,"WEBP")
        self.assertIn("hd-dataflair-logo",self.home)
        self.assertIn("dataflairLogo=key==='dataflair web services pvt ltd'",self.home)
        self.assertIn("dataflair_logo = company.casefold()",self.generator)
        hero=(ROOT/"assets/job-hero.css").read_text(encoding="utf-8")
        self.assertIn(".hdj3-logo.hd-dataflair-logo{width:80px",hero)
        self.assertIn(".hd-logo-summary.hd-dataflair-logo{width:80px",hero)
        self.assertIn(".company-logo.hd-dataflair-logo{width:80px",self.home)

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


    def test_employer_logo_presentation_is_shared_by_home_and_job_pages(self):
        display=(ROOT/"assets/employer-logo-display.js").read_text(encoding="utf-8")
        hero=(ROOT/"assets/job-hero.css").read_text(encoding="utf-8")
        self.assertIn('assets/employer-logo-display.js',self.home)
        self.assertIn('../assets/employer-logo-display.js',self.generator)
        self.assertIn('data-hd-employer-logo="1"',self.home)
        self.assertIn('data-hd-employer-logo="1"',self.generator)
        self.assertIn('hd-logo-summary hd-owner-logo',self.generator)
        self.assertIn('$summary_logo',self.generator)
        self.assertIn('owner_logo = favicon_url.startswith("../assets/company-owner/")',self.generator)
        self.assertIn('w-[72%] h-[72%]',self.generator)
        for key in ("SAMPLE = 64","source.origin !== location.origin",
                    "white / visible > 0.74", "bw / Math.max(1, bh) >= 3.15",
                    "hd-logo-dark", "hd-logo-initials"):
            self.assertIn(key,display)
        self.assertIn('.company-logo.hd-owner-logo.hd-logo-dark',self.home)
        self.assertIn('.hdj3-logo.hd-owner-logo.hd-logo-dark',hero)
        self.assertIn('.hd-logo-summary.hd-owner-logo.hd-logo-dark',hero)
        self.assertIn("ownerLogo=String(first||'').startsWith('assets/company-owner/')",self.home)
        self.assertIn('w-[94%] h-[94%]',self.home)
        self.assertIn('width:83%',hero)
        self.assertIn("assetPath.startsWith('/assets/company-owner/')",display)
        self.assertIn('width:96%',hero)
        # Wide logos use the existing initials instead of being shrunk further.
        self.assertIn('ratio >= 3.15',display)
        # Image delivery remains local and does not overwrite approved files.
        self.assertNotIn('fetch(',display)
        self.assertNotIn('toDataURL(',display)


    def test_latest_owner_selected_employer_logos_have_priority(self):
        # Uploaded assets are the final source of truth, ahead of ATS and cached icons.
        for company in ("Drivetrain","Endeavor IT Solution","Pentoz Technology","Swappit Web & Software Solutions","Central Pulp & Paper Research Institute","Hyreo","Taurus Hard Soft Solutions Pvt Ltd","MarkTeQ","Zynga","WNS Global Services","KredX","Zeta","Blueberry Labs","Capco"):
            with self.subTest(company=company):
                path=self.approved.get(company)
                self.assertTrue(path and path.startswith("assets/company-owner/"),company)
                self.assertTrue((ROOT/path).is_file(),company)
        self.assertIn("const approved=",self.home)
        self.assertIn("const sources=[approved,cached,local,direct]",self.home)
        self.assertIn("sources = [",self.generator)
        self.assertIn("approved if approved else",self.generator)

if __name__=="__main__":
    unittest.main()
