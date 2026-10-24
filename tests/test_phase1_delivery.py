import io
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import publish_verified_telegram as telegram


class Response:
    status = 200

    def __init__(self, content):
        self.content = content.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, length):
        return self.content[:length]


JOB = {
    "page": "jobs/example-data-engineer.html",
    "company": "Example",
    "role": "Data Engineer",
}


def document(label):
    return (
        "<html><head><title>Example Data Engineer | HD Careers</title>"
        '<link rel="canonical" href="https://hdcareers.in/jobs/example-data-engineer.html">'
        "</head><body>" + label + "</body></html>"
    )


class DeploymentProofTests(unittest.TestCase):
    def check(self, label):
        with patch.object(telegram, "urlopen", return_value=Response(document(label))):
            return telegram.live_job(JOB)

    def test_valid_live_page_does_not_need_jobposting_schema(self):
        self.assertTrue(self.check("<strong>Verified active:</strong> Official source checked."))

    def test_verification_pending_must_not_trigger_telegram(self):
        self.assertFalse(self.check("<strong>Verification pending:</strong> Not confirmed."))

    def test_expired_page_must_not_trigger_telegram(self):
        self.assertFalse(self.check("<strong>Application status:</strong> Application closed."))

    def test_incorrect_title_must_not_trigger_telegram(self):
        with patch.object(telegram, "urlopen", return_value=Response(
            document("<strong>Verified active:</strong>").replace(
                "<title>Example Data Engineer", "<title>Different Employer Other Role"
            )
        )):
            self.assertFalse(telegram.live_job(JOB))

    def test_missing_or_wrong_canonical_must_not_trigger_telegram(self):
        with patch.object(telegram, "urlopen", return_value=Response(
            document("<strong>Verified active:</strong>").replace(
                "jobs/example-data-engineer.html", "jobs/some-other-role.html"
            )
        )):
            self.assertFalse(telegram.live_job(JOB))

    def test_network_error_fails_closed(self):
        with patch.object(telegram, "urlopen", side_effect=TimeoutError):
            self.assertFalse(telegram.live_job(JOB))


class WorkflowSafetyTests(unittest.TestCase):
    def read(self, filename):
        return (ROOT / ".github" / "workflows" / filename).read_text()

    def test_duplicate_generator_only_runs_manually(self):
        content = self.read("generate-job-pages.yml")
        self.assertIn("workflow_dispatch:", content)
        self.assertNotIn("  push:", content)
        self.assertIn("group: main-job-data-publish", content)
        self.assertNotIn("git add -A", content)

    def test_telegram_sender_push_is_only_for_approved_manifest(self):
        content = self.read("publish-verified-telegram.yml")
        self.assertIn("workflow_dispatch:", content)
        self.assertIn("  push:", content)
        push_section = content.split("  push:", 1)[1].split("  workflow_dispatch:", 1)[0]
        watched_paths = re.findall(r"^\s+- (data/[^\n ]+)", push_section, re.M)
        self.assertEqual(watched_paths, ["data/telegram-approved-batch.json"])
        self.assertIn("group: main-job-data-publish", content)
        self.assertIn("scripts/publish_approved_telegram.py", content)

    def test_unsafe_legacy_sender_retired(self):
        self.assertFalse((ROOT / ".github" / "workflows" / "telegram-owner-batch-20261010.yml").exists())

    def test_twice_daily_checker_preserved(self):
        self.assertIn("45 2,14 * * *", self.read("job-availability.yml"))


if __name__ == "__main__":
    unittest.main()
