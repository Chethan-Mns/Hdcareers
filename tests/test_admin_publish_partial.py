"""Safety tests for approved mixed Live / Review / Expired VIP batches."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import admin_publish

def job(company, role, code):
    return {
        "page": f"jobs/{company.lower()}-{code}.html",
        "domain": "jobs.example.com",
        "company": company,
        "salary": "Not Disclosed",
        "logo": [company[:2].upper(), "#111111"],
        "role": role,
        "roleTag": role,
        "loc": "Bengaluru",
        "locationFilter": "Bengaluru",
        "batch": "Not specified",
        "elig": "Refer official posting",
        "cat": "it",
        "expType": "fresher",
        "expYears": "Entry level",
        "date": "Not specified",
        "desc": "Official job opportunity",
        "resp": ["Work on team software tasks"],
        "skills": ["Python"],
        "apply": f"https://jobs.example.com/{code}",
        "status": "active",
        "verifiedDate": "17 Oct 2026",
        "sourceName": "Official posting",
        "who": "Eligible candidates per official listing",
        "workMode": "Not specified"
    }


class PartialVipPublishingTests(unittest.TestCase):
    def run_publisher(self, states):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            data, review, manifest, event = [root / x for x in ("jobs.json", "review.json", "approved.json", "event.json")]
            data.write_text("[]")
            review.write_text("[]")
            incoming = [job(f"Company{i}", f"Role {i}", str(i)) for i in range(len(states))]
            event.write_text(json.dumps({"client_payload": {"jobs": incoming}}))
            def check(j):
                i = int(j["apply"].split("/")[-1])
                return {"state": states[i], "reason": f"test {states[i]}", "checkedAt": "2026-10-17T05:00:00Z"}
            with patch.object(admin_publish, "DATA_FILE", data), patch.object(admin_publish, "REVIEW_FILE", review), patch.object(admin_publish, "APPROVED_BATCH", manifest), patch.object(admin_publish, "check", side_effect=check), patch.object(sys, "argv", ["admin_publish.py", str(event)]):
                admin_publish.main()
            return json.loads(data.read_text()), json.loads(review.read_text()), json.loads(manifest.read_text()) if manifest.exists() else None

    def test_only_live_subset_is_published(self):
        published, held, manifest = self.run_publisher(["active", "review", "expired", "active"])
        self.assertEqual([j["role"] for j in published], ["Role 0", "Role 3"])
        self.assertEqual([j["role"] for j in (x["job"] for x in held)], ["Role 1"])
        self.assertEqual(manifest["pages"], [j["page"] for j in published])
        self.assertEqual(len(set(manifest["pages"])), 2)

    def test_all_uncertain_yields_no_publication_or_telegram_manifest(self):
        published, held, manifest = self.run_publisher(["review", "review"])
        self.assertEqual(published, [])
        self.assertEqual(len(held), 2)
        self.assertIsNone(manifest)

    def test_all_expired_yields_no_publication(self):
        published, held, manifest = self.run_publisher(["expired", "expired"])
        self.assertEqual(published, [])
        self.assertEqual(held, [])
        self.assertIsNone(manifest)


if __name__ == "__main__":
    unittest.main()
