import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import phase4_growth_audit
import generate

class GrowthTests(unittest.TestCase):
    def test_growth_audit_is_non_mutating_and_includes_required_trust_checks(self):
        result = phase4_growth_audit.audit(ROOT)
        self.assertEqual(result["mode"], "read_only")
        self.assertFalse(result["websiteWritten"])
        self.assertFalse(result["telegramSent"])
        self.assertFalse(result["adSenseApprovalGuaranteed"])
        self.assertGreater(result["metrics"]["jobPages"], 50)

    def test_new_job_pages_have_social_image_and_summaries(self):
        template = generate.PAGE_TEMPLATE.template
        self.assertIn('<meta property="og:image"', template)
        self.assertIn('<meta name="twitter:card" content="summary">', template)
        self.assertIn('<meta name="twitter:title"', template)
        self.assertIn('<meta property="og:site_name"', template)

    def test_resume_readers_not_loaded_until_upload(self):
        template = generate.PAGE_TEMPLATE.template
        self.assertNotIn('<script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js', template)
        self.assertNotIn('<script src="https://cdnjs.cloudflare.com/ajax/libs/mammoth', template)
        self.assertIn("function ensureResumeReader(kind)", template)
        self.assertIn("await ensureResumeReader('pdf')", template)
        self.assertIn("await ensureResumeReader('docx')", template)

    def test_analytics_optout_and_private_queries(self):
        script = (ROOT / "assets/analytics.js").read_text()
        self.assertIn("hd_analytics_optout", script)
        self.assertIn("hd_web_vital", script)
        self.assertNotIn("window.location.search", script)
        self.assertIn("metric_name: \"LCP\"", script)

if __name__ == "__main__":
    unittest.main()
