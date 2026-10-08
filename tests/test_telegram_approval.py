import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import publish_approved_telegram as pub


class TelegramApprovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.manifest = Path(self.tmp.name) / "telegram-approved-batch.json"
        self.ledger = Path(self.tmp.name) / "telegram-deliveries.json"
        self.manifest.write_text(json.dumps({"approved": True, "batchId": "approved-001", "pages": ["jobs/test-a.html", "jobs/test-b.html"]}))
        self.jobs = [
            {"page": "jobs/test-a.html", "status": "active", "company": "Company A"},
            {"page": "jobs/test-b.html", "status": "active", "company": "Company B"},
        ]
        self.patches = [
            patch.object(pub, "MANIFEST", self.manifest),
            patch.object(pub, "LEDGER", self.ledger),
            patch.object(pub, "load_current_jobs", return_value=self.jobs),
            patch.object(pub, "wait_for_exact_page", return_value=True),
            patch.object(pub, "check", return_value={"state": "active"}),
            patch.object(pub, "message_for", side_effect=lambda j: j["page"]),
            patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-bot-token", "TELEGRAM_CHANNEL_ID": "@HD_Careers", "JOB_PAGES": ""}),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def test_sends_and_deduplicates_with_receipts(self):
        with patch.object(pub, "send_telegram", side_effect=[101, 102]) as send:
            pub.publish()
            self.assertEqual(send.call_count, 2)
        state = json.loads(self.ledger.read_text())
        self.assertEqual(state["@HD_Careers|jobs/test-a.html"]["messageId"], 101)
        self.assertEqual(state["@HD_Careers|jobs/test-b.html"]["messageId"], 102)
        with patch.object(pub, "send_telegram") as send:
            pub.publish()
            send.assert_not_called()

    def test_requires_approval(self):
        self.manifest.write_text(json.dumps({"approved": False, "batchId": "test", "pages": ["jobs/test-a.html"]}))
        with self.assertRaises(SystemExit):
            pub.publish()

    def test_preflight_failure_does_not_send_any_job(self):
        with patch.object(pub, "wait_for_exact_page", side_effect=[True, False]):
            with patch.object(pub, "send_telegram") as send:
                with self.assertRaises(SystemExit):
                    pub.publish()
                send.assert_not_called()

    def test_partial_failure_is_recorded_and_retry_skips_success(self):
        with patch.object(pub, "send_telegram", side_effect=[101, RuntimeError("Telegram HTTP 429: retry later")]):
            with self.assertRaises(RuntimeError):
                pub.publish()
        state = json.loads(self.ledger.read_text())
        self.assertEqual(state["@HD_Careers|jobs/test-a.html"]["status"], "delivered")
        self.assertEqual(state["@HD_Careers|jobs/test-b.html"]["status"], "failed")
        with patch.object(pub, "send_telegram", return_value=102) as send:
            pub.publish()
            self.assertEqual(send.call_count, 1)

    def test_unknown_delivery_outcome_blocks_automatic_retry(self):
        with patch.object(pub, "send_telegram", side_effect=[101, TimeoutError("network")]):
            with self.assertRaises(TimeoutError):
                pub.publish()
        state = json.loads(self.ledger.read_text())
        self.assertEqual(state["@HD_Careers|jobs/test-b.html"]["status"], "uncertain")
        with patch.object(pub, "send_telegram") as send:
            with self.assertRaises(SystemExit):
                pub.publish()
            send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
