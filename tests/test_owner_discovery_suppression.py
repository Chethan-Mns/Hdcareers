"""Owner-expired requisitions are suppressed only from fresher discovery."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import discovery_ats_shadow as scanner

URL = "https://gehc.wd5.myworkdayjobs.com/en-US/GEHC_ExternalSite/job/Graduate-Trainee-Engineer_R4043154-1"
RECORD = {
    "company": "GE HealthCare", "provider": "workday",
    "sourceBoard": "GEHC_ExternalSite",
    "officialUrl": URL, "requisitionId": "R4043154",
    "decision": "expired", "sourceBatchId": "2026-11-01-freehire-style-20",
}


class OwnerSuppressionTests(unittest.TestCase):
    def candidate(self, req="R4043154-1", company="GE HealthCare"):
        return {
            "company": company,
            "sourceProvider": "workday",
            "sourceBoard": "GEHC_ExternalSite",
            "externalId": "/job/Bengaluru/Graduate-Trainee-Engineer_" + req,
            "apply": "https://gehc.wd5.myworkdayjobs.com/GEHC_ExternalSite/job/Bengaluru/Graduate-Trainee-Engineer_" + req,
        }

    def test_exact_url_and_workday_requisition_match(self):
        c = self.candidate()
        self.assertIsNotNone(scanner.owner_suppression_match(c, [RECORD]))
        self.assertIsNotNone(scanner.owner_suppression_match({
            **c, "apply": URL, "externalId": "different"}, [RECORD]))

    def test_different_requisition_or_company_not_suppressed(self):
        for c in [
            self.candidate("R40431540-1"),
            self.candidate("R4043155-1"),
            self.candidate(company="Unrelated HealthCare"),
            {**self.candidate(), "sourceBoard": "DifferentSite"},
        ]:
            with self.subTest(c=c):
                self.assertIsNone(scanner.owner_suppression_match(c, [RECORD]))

    def test_load_owner_decision_file(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "ledger.json"
            p.write_text(json.dumps({
                "schemaVersion": 1, "mode": "owner_discovery_suppression",
                "records": [RECORD]}))
            self.assertEqual(scanner.load_owner_suppression(p), [RECORD])
            p.write_text(json.dumps({"schemaVersion": 999, "records": [RECORD]}))
            with self.assertRaises(ValueError):
                scanner.load_owner_suppression(p)

    def test_owner_expired_is_not_a_new_review_candidate(self):
        published = [{
            "company": "GE HealthCare",
            "role": "Unrelated old requisition",
            "apply": "https://gehc.wd5.myworkdayjobs.com/GEHC_ExternalSite/job/Old_R1234567",
        }]
        board = scanner.boards_from_jobs(published)[0]
        self.assertEqual(board["provider"], "workday")
        def posting(req):
            return {
                "id": "/job/Bengaluru/Graduate-Trainee-Engineer_" + req,
                "url": "https://gehc.wd5.myworkdayjobs.com/GEHC_ExternalSite/job/Bengaluru/Graduate-Trainee-Engineer_" + req,
                "title": "Graduate Trainee Engineer", "location": "Bengaluru, India",
                "description": "Graduate trainee engineering role",
            }
        with patch.object(scanner, "source_posts",
                          return_value=([posting("R4043154-1"), posting("R40431540-1")], [], True)):
            result = scanner.discover(published, suppressed=[RECORD])
        self.assertEqual(result["excludedByOwnerExpired"], 1)
        self.assertEqual(result["candidateCount"], 1)
        self.assertTrue(result["candidates"][0]["apply"].endswith("R40431540-1"))
        self.assertEqual(result["scans"][0]["excludedByOwnerExpired"], 1)
        self.assertEqual(result["excludedCandidates"][0]["duplicateReason"], "owner_expired")
        self.assertFalse(result["publicationAllowed"])
        self.assertFalse(result["expiryDecisionsAllowed"])

    def test_personal_profile_not_changed_by_fresher_owner_exclusions(self):
        self.assertIsNone(scanner.owner_suppression_match({
            "company": "GE HealthCare", "sourceProvider": "lever",
            "apply": "https://jobs.lever.co/ge-healthcare/de-123",
            "externalId": "de-123",
        }, [RECORD]))


if __name__ == "__main__":
    unittest.main()
