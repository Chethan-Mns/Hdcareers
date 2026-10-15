import json
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from phase2_owner_20_readonly import historic_assessment, current_db_assessment

class OwnerBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads((ROOT / "tests/fixtures/owner_phase2_manual_20_20261014.json").read_text())
        cls.jobs = {int(j["id"]): j for j in json.loads((ROOT / "data/jobs.json").read_text())}

    def test_all_20_exact_company_urls_exist(self):
        cases = self.fixture["samples"]
        self.assertEqual(len(cases), 20)
        self.assertEqual(len({r["id"] for r in cases}), 20)
        for r in cases:
            self.assertIn(r["id"], self.jobs)
            self.assertEqual(self.jobs[r["id"]]["company"], r["company"])
            self.assertEqual(self.jobs[r["id"]]["apply"], r["url"])

    def test_owner_truth_is_16_live_four_expired(self):
        self.assertEqual(Counter(x["userVerdict"] for x in self.fixture["samples"]), {"live": 16, "expired": 4})

    def test_historical_baseline_is_13_right_two_false_expired_five_review(self):
        c = Counter(historic_assessment(r["recordedChecker"], r["userVerdict"]) for r in self.fixture["samples"])
        self.assertEqual(c, {"correct": 13, "false_expired": 2, "inconclusive_resolved_by_owner": 5})
        self.assertEqual({r["id"] for r in self.fixture["samples"] if historic_assessment(r["recordedChecker"], r["userVerdict"])=="false_expired"}, {75, 82})

    def test_service_now_reconciled_and_two_known_false_expired_are_still_visible(self):
        wrong = {r["id"] for r in self.fixture["samples"] if current_db_assessment(self.jobs[r["id"]].get("status"), r["userVerdict"]) != "agrees_with_owner"}
        # Characterization assertion: do not remove these defects from the
        # benchmark; the production release gate checks for their correction.
        self.assertTrue({75, 82}.issubset(wrong))
        self.assertNotIn(104, wrong)

    def test_trusted_source_list_has_no_fabricated_url(self):
        self.assertTrue(all(r["url"].startswith("https://") and r["url"] == self.jobs[r["id"]]["apply"] for r in self.fixture["samples"]))

if __name__ == "__main__":
    unittest.main()
