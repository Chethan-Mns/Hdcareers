"""Offline safety tests for the Synopsys one-post WhatsApp OG image preview trial."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import whapi_premium_preview_trial as preview


class WhatsAppPreviewTrialTests(unittest.TestCase):
    def test_exact_target_and_isolation(self):
        self.assertEqual(preview.PAGE, "jobs/synopsys-cad-design-support-apprenticeship.html")
        self.assertEqual(preview.IMAGE, "assets/job-previews/synopsys-cad-design-support-apprenticeship.png")
        self.assertEqual(preview.SIZE, (1200, 630))
        self.assertTrue(preview.PUBLIC_IMAGE.startswith("https://hdcareers.in/assets/job-previews/"))

    def test_injects_social_image_only_into_exact_job(self):
        html = '<html><head><meta property="og:url" content="' + preview.PUBLIC_JOB + '"></head></html>'
        modified = preview.inject_meta(html)
        self.assertIn('property="og:image" content="' + preview.PUBLIC_IMAGE + '"', modified)
        self.assertIn('property="og:image:width" content="1200"', modified)
        self.assertIn('property="og:image:height" content="630"', modified)
        self.assertIn('name="twitter:card" content="summary_large_image"', modified)
        self.assertEqual(modified.count('property="og:image"'), 1)
        with self.assertRaises(RuntimeError):
            preview.inject_meta(modified)
        with self.assertRaises(RuntimeError):
            preview.inject_meta('<meta property="og:url" content="https://wrong.example/page">')

    def test_render_premium_png_with_company_logo(self):
        with tempfile.TemporaryDirectory() as tmp:
            logo = Path(tmp) / "synopsys.png"
            image = Image.new("RGBA", (400, 163), "#ffffff")
            image.save(logo)
            dest = Path(tmp) / "card.png"
            preview.render({"company": "Synopsys",
                            "role": "CAD / Design Support Apprenticeship",
                            "loc": "Noida, Uttar Pradesh, India"}, logo, dest)
            with Image.open(dest) as result:
                self.assertEqual(result.format, "PNG")
                self.assertEqual(result.size, (1200, 630))
            self.assertLess(dest.stat().st_size, 800_000)

    def test_only_next_pending_job_can_receive_trial(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir()
            queue = {"items": [
                {"page": preview.PAGE, "status": "pending",
                 "dueAt": "2026-11-22T11:36:54+00:00"},
                {"page": "jobs/another.html", "status": "pending",
                 "dueAt": "2026-11-22T12:36:54+00:00"},
            ]}
            (root / "data/telegram-hourly-queue.json").write_text(json.dumps(queue))
            (root / "data/whatsapp-channel-deliveries.json").write_text(
                json.dumps({"version": 1, "items": {}}))
            self.assertEqual(preview.check_next_job(root), "2026-11-22T11:36:54+00:00")
            queue["items"][1]["dueAt"] = "2026-11-22T10:36:54+00:00"
            (root / "data/telegram-hourly-queue.json").write_text(json.dumps(queue))
            with self.assertRaises(RuntimeError):
                preview.check_next_job(root)
            queue["items"][1]["dueAt"] = "2026-11-22T12:36:54+00:00"
            (root / "data/telegram-hourly-queue.json").write_text(json.dumps(queue))
            (root / "data/whatsapp-channel-deliveries.json").write_text(
                json.dumps({"version": 1, "items": {preview.PAGE: {"status": "sending"}}}))
            with self.assertRaises(RuntimeError):
                preview.check_next_job(root)


if __name__ == "__main__":
    unittest.main()
