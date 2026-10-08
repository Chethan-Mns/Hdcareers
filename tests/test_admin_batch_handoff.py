from __future__ import annotations
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import admin_publish as admin


class ApprovedBatchHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.jobs_file = self.root / "jobs.json"
        self.reviews_file = self.root / "review-queue.json"
        self.batch_file = self.root / "telegram-approved-batch.json"
        self.event_file = self.root / "event.json"
        self.existing = [{"id": 20, "company": "Existing", "role": "Old", "apply": "https://example.com/old", "page": "jobs/existing.html"}]
        self.jobs_file.write_text(json.dumps(self.existing))
        self.reviews_file.write_text("[]")
        for patcher in (
            patch.object(admin, "DATA_FILE", self.jobs_file),
            patch.object(admin, "REVIEW_FILE", self.reviews_file),
            patch.object(admin, "APPROVED_BATCH", self.batch_file),
            patch.object(sys, "argv", ["admin_publish.py", str(self.event_file)]),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    @staticmethod
    def candidate(index):
        return {
            "page": "", "domain": "example.com", "company": f"Company {index}", "salary": "Not Disclosed",
            "logo": [f"C{index}", "#374151"], "role": f"Role {index}", "roleTag": f"Role {index}",
            "loc": "India", "locationFilter": "India", "batch": "Not Specified",
            "elig": "See official listing", "cat": "nonit" if index == 1 else "it",
            "expType": "not-specified" if index == 1 else "fresher", "expYears": "Not Specified",
            "date": "09 Oct 2026", "desc": "Official vacancy", "resp": ["Apply via official source"],
            "apply": f"https://example.com/job/{index}", "status": "active", "verifiedDate": "09 Oct 2026",
            "sourceName": "Official careers", "skills": [] if index == 1 else ["Python"],
            "who": "Read official eligibility", "workMode": "Not Specified",
        }

    def write_event(self, count=10):
        payload = {"client_payload": {"jobs": [self.candidate(i) for i in range(1, count + 1)]}}
        self.event_file.write_text(json.dumps(payload))

    def test_ten_approved_jobs_create_ten_pages_and_one_manifest(self):
        self.write_event()
        with patch.object(admin, "check", side_effect=lambda j: {"state": "active", "reason": "exact official job verified"}):
            admin.main()
        current = json.loads(self.jobs_file.read_text())
        batch = json.loads(self.batch_file.read_text())
        self.assertEqual(len(current), 11)
        self.assertEqual(len(batch["pages"]), 10)
        self.assertEqual(len(set(batch["pages"])), 10)
        self.assertTrue(batch["approved"])
        self.assertEqual(current[0]["cat"], "nonit")
        self.assertEqual(current[0]["skills"], [])

    def test_one_unconfirmed_blocks_entire_batch(self):
        self.write_event()
        with patch.object(admin, "check", side_effect=lambda j: {"state": "review" if j["company"] == "Company 5" else "active", "reason": "needs exact review"}):
            with self.assertRaisesRegex(SystemExit, "9 of 10 passed, 1 need manual review"):
                admin.main()
        self.assertEqual(json.loads(self.jobs_file.read_text()), self.existing)
        self.assertFalse(self.batch_file.exists())

    def test_one_expired_blocks_entire_batch(self):
        self.write_event()
        with patch.object(admin, "check", side_effect=lambda j: {"state": "expired" if j["company"] == "Company 4" else "active", "reason": "closed"}):
            with self.assertRaisesRegex(SystemExit, "1 were closed"):
                admin.main()
        self.assertEqual(json.loads(self.jobs_file.read_text()), self.existing)
        self.assertFalse(self.batch_file.exists())


if __name__ == "__main__":
    unittest.main()
