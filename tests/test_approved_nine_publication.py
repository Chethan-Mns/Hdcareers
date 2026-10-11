from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "prepare_review_publication.py"
SPEC = importlib.util.spec_from_file_location("approved_partial", SOURCE)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)

KEYS = ("page", "domain", "company", "salary", "logo", "role", "roleTag", "loc",
        "locationFilter", "batch", "elig", "cat", "expType", "expYears", "date",
        "desc", "resp", "apply", "status", "verifiedDate", "sourceName", "skills", "who", "workMode")


def job(i: int) -> dict:
    result = {
        "page": f"jobs/employer-{i}.html", "domain": "careers.example.com",
        "company": f"Employer {i}", "salary": "Not Disclosed",
        "logo": ["EM", "#2345ff"], "role": f"Developer {i}",
        "roleTag": "Developer", "loc": "Bengaluru", "locationFilter": "Bengaluru",
        "batch": "Not Specified", "elig": "Degree", "cat": "it",
        "expType": "fresher", "expYears": "0 years", "date": "11 Oct 2026",
        "desc": "Verified employer description", "resp": ["Build software"],
        "apply": f"https://careers.example.com/jobs/{i}", "status": "active",
        "verifiedDate": "11 Oct 2026", "sourceName": "Employer Careers",
        "skills": [], "who": "Degree holder", "workMode": "Not Specified",
        "manualLiveVerifiedAt": "2026-10-11T05:45:00.000Z"
    }
    return result


class TestExplicitNineJobPublication(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.old_daily, self.old_published = MOD.DAILY, MOD.PUBLISHED
        MOD.DAILY = root / "daily-review-batch.json"
        MOD.PUBLISHED = root / "jobs.json"
        self.request = root / "request.json"
        self.output = root / "event.json"
        self.rows = []
        for n in range(9):
            self.rows.append({
                "id": f"approved-{n}", "reviewedStatus": "live",
                "reviewedAt": "2026-10-11T05:45:00.000Z",
                "apply": f"https://careers.example.com/jobs/{n}",
                "job": job(n)
            })
        self.batch = {"batchId": "2026-10-11-0900-ist", "status": "reviewing",
                      "priority": list(self.rows), "backup": []}
        self.request_data = {
            "batchId": "2026-10-11-0900-ist", "candidateIds": [x["id"] for x in self.rows],
            "approvedBy": "HD Careers Owner", "requestId": "approved-nine-20261011"
        }
        MOD.PUBLISHED.write_text("[]")
        self.save()

    def tearDown(self):
        MOD.DAILY, MOD.PUBLISHED = self.old_daily, self.old_published
        self.tmp.cleanup()

    def save(self):
        MOD.DAILY.write_text(json.dumps(self.batch))
        self.request.write_text(json.dumps(self.request_data))

    def test_nine_named_human_verified_jobs_create_existing_publish_event(self):
        data = MOD.prepare(self.request, self.output)
        self.assertEqual(data["jobCount"], 9)
        self.assertEqual(data["excluded"], ["Unisys"])
        event = json.loads(self.output.read_text())
        self.assertEqual(event["event_type"], "admin_publish_jobs")
        self.assertEqual(len(event["client_payload"]["jobs"]), 9)
        self.assertTrue(all(x["manualLiveVerifiedUrl"] == x["apply"] for x in event["client_payload"]["jobs"]))
        self.assertEqual(self.rows[0]["job"].get("manualLiveVerifiedUrl"), None)

    def test_unreviewed_job_is_never_published(self):
        self.batch["priority"][3]["reviewedStatus"] = "unreviewed"
        self.save()
        with self.assertRaisesRegex(ValueError, "LIVE"):
            MOD.prepare(self.request, self.output)

    def test_incomplete_job_is_never_published(self):
        del self.batch["priority"][2]["job"]["elig"]
        self.save()
        with self.assertRaisesRegex(ValueError, "missing publication"):
            MOD.prepare(self.request, self.output)

    def test_expired_job_is_never_published(self):
        self.batch["priority"][0]["job"]["status"] = "expired"
        self.save()
        with self.assertRaisesRegex(ValueError, "active"):
            MOD.prepare(self.request, self.output)

    def test_do_not_allow_unisys_or_silent_extra_job(self):
        self.request_data["candidateIds"][0] = "unisys-REQ568332"
        self.save()
        with self.assertRaisesRegex(ValueError, "Unisys"):
            MOD.prepare(self.request, self.output)
        self.request_data["candidateIds"].append("unexpected-job")
        self.save()
        with self.assertRaisesRegex(ValueError, "nine"):
            MOD.prepare(self.request, self.output)

    def test_duplicate_previously_published_blocks_repeat(self):
        MOD.PUBLISHED.write_text(json.dumps([job(0)]))
        with self.assertRaisesRegex(ValueError, "already appears in production"):
            MOD.prepare(self.request, self.output)

    def test_wrong_batch_or_owner_rejected(self):
        self.batch["batchId"] = "older-batch"
        self.save()
        with self.assertRaisesRegex(ValueError, "does not match"):
            MOD.prepare(self.request, self.output)
        self.batch["batchId"] = self.request_data["batchId"]
        self.request_data["approvedBy"] = "automatic"
        self.save()
        with self.assertRaisesRegex(ValueError, "Owner publication approval"):
            MOD.prepare(self.request, self.output)

    def test_manual_verification_must_match_original_requisition_and_time(self):
        self.batch["priority"][0]["job"]["manualLiveVerifiedAt"] = "2026-10-10T00:00:00Z"
        self.save()
        with self.assertRaisesRegex(ValueError, "timestamp"):
            MOD.prepare(self.request, self.output)
        self.batch["priority"][0]["job"]["manualLiveVerifiedAt"] = self.batch["priority"][0]["reviewedAt"]
        self.batch["priority"][0]["job"]["apply"] = "https://careers.example.com/jobs/changed"
        self.save()
        with self.assertRaisesRegex(ValueError, "Official URL changed"):
            MOD.prepare(self.request, self.output)


if __name__ == "__main__":
    unittest.main()
