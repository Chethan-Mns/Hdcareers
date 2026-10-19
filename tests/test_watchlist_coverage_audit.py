import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from watchlist_coverage_audit import audit


class WatchlistCoverageTests(unittest.TestCase):
    def setUp(self):
        self.watchlist = json.loads((ROOT / "data" / "employer-watchlist-87.json").read_text(encoding="utf-8"))

    def test_87_unique_employers_and_stages(self):
        result = audit(self.watchlist)
        self.assertEqual(result["targetEmployers"], 87)
        self.assertEqual(len(result["items"]), 87)
        self.assertEqual(result["counts"]["partial_full_list_shadow"], 4)
        self.assertEqual(result["counts"]["official_portal_probe_only"], 7)
        self.assertEqual(result["counts"]["no_official_source_adapter"], 76)
        self.assertFalse(result["all87CompletelySearched"])
        self.assertFalse(result["autoPublishEnabled"])

    def test_deloitte_mapping_does_not_claim_usi_coverage(self):
        result = audit(self.watchlist)
        deloitte = next(x for x in result["items"] if x["company"] == "Deloitte")
        self.assertEqual(deloitte["mappedSource"], "Deloitte South Asia")
        self.assertEqual(deloitte["coverage"], "partial_full_list_shadow")
        self.assertTrue(any("Deloitte USI" in note for note in result["notes"]))

    def test_reject_missing_or_duplicate_company(self):
        modified = json.loads(json.dumps(self.watchlist))
        modified["categories"]["retail-business"][-1] = "Deloitte"
        with self.assertRaises(ValueError):
            audit(modified)


if __name__ == "__main__":
    unittest.main()
