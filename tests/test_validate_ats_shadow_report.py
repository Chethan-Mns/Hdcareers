import sys
import unittest
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_ats_shadow_report import audit


def sample():
    report = {
        "mode": "shadow_only", "profile": "fresher",
        "publicationAllowed": False, "expiryDecisionsAllowed": False,
        "totalSeedBoards": 1, "scannedBoards": 1,
        "candidateCount": 1, "partialOrFailedBoards": 0,
        "scans": [{"company": "Acme", "board": "acme", "status": "ok", "complete": True}],
        "candidates": [{
            "id": "ats-abc", "company": "Acme", "role": "Graduate Engineer Trainee",
            "loc": "Bengaluru, India", "apply": "https://job-boards.greenhouse.io/acme/jobs/112",
            "externalId": "112", "sourceProvider": "greenhouse", "sourceBoard": "acme",
            "eligibilityStatus": "needs_manual_verification", "reviewedStatus": "unreviewed",
            "searchProfile": "fresher", "descriptionExcerpt": "0-2 years experience",
        }],
    }
    return report


class RealExtractionGateTests(unittest.TestCase):
    def test_valid_realistic_candidate(self):
        out = audit(sample(), [])
        self.assertTrue(out["passed"], out["errors"])
        self.assertEqual(out["employers"], 1)

    def test_a_posting_already_published_is_not_reintroduced(self):
        r = sample()
        out = audit(r, [{"company": "Acme", "role": "Graduate Engineer Trainee",
                         "apply": r["candidates"][0]["apply"]}])
        self.assertFalse(out["passed"])

    def test_wrong_board_and_nonindia_are_rejected(self):
        r = sample()
        r["candidates"][0]["apply"] = "https://job-boards.greenhouse.io/other/jobs/112"
        r["candidates"][0]["loc"] = "London, UK"
        self.assertFalse(audit(r, [])["passed"])

    def test_india_country_evidence_sufficient_when_location_is_remote(self):
        r = sample()
        r["candidates"][0]["loc"] = "Remote"
        r["candidates"][0]["countryEvidence"] = "IN"
        self.assertTrue(audit(r, [])["passed"])
        r["candidates"][0]["countryEvidence"] = "US"
        self.assertFalse(audit(r, [])["passed"])

    def test_long_source_description_preserves_classification_evidence(self):
        r = sample()
        r["candidates"][0]["role"] = "Quality Engineer"
        r["candidates"][0]["descriptionExcerpt"] = "Company background " * 70
        r["candidates"][0]["descriptionForValidation"] = (
            r["candidates"][0]["descriptionExcerpt"] + " 0-2 years experience")
        self.assertTrue(audit(r, [])["passed"], audit(r, [])["errors"])
        r["candidates"][0].pop("descriptionForValidation")
        self.assertFalse(audit(r, [])["passed"])

    def test_expiry_or_publication_mutations_are_blocked(self):
        for key in ("expiryDecisionsAllowed", "publicationAllowed"):
            r = sample()
            r[key] = True
            self.assertFalse(audit(r, [])["passed"])

    def test_stale_and_partial_scans_cannot_be_labeled_complete(self):
        r = sample()
        r["scans"][0].update(status="ok", complete=False)
        r["partialOrFailedBoards"] = 1
        self.assertFalse(audit(r, [])["passed"])
        r["scans"][0]["status"] = "partial"
        self.assertTrue(audit(r, [])["passed"])
        self.assertTrue(audit(r, [])["warnings"])

    def test_cross_profile_and_duplicates_rejected(self):
        r = sample()
        r["candidates"][0]["searchProfile"] = "data-engineer-2y"
        self.assertFalse(audit(r, [])["passed"])
        r = sample()
        r["candidates"].append(deepcopy(r["candidates"][0]))
        r["candidateCount"] = 2
        self.assertFalse(audit(r, [])["passed"])

    def test_data_engineer_profile_is_only_personal(self):
        r = sample()
        r["profile"] = "data-engineer-2y"
        r["candidates"][0]["role"] = "Data Engineer"
        r["candidates"][0]["descriptionExcerpt"] = "2 years experience in Python SQL and Snowflake"
        r["candidates"][0]["searchProfile"] = "data-engineer-2y"
        self.assertTrue(audit(r, [])["passed"])
        r["candidates"][0]["role"] = "Senior Data Engineer"
        self.assertFalse(audit(r, [])["passed"])


if __name__ == "__main__":
    unittest.main()
