import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from discovery_v3_gate import inspect_history

IST = timezone(timedelta(hours=5, minutes=30))
DAY = datetime(2026, 10, 9, 8, 30, tzinfo=IST)
EVIDENCE = ["canonical-match", "title-match", "apply-control"]


def run(offset, *, complete=True, ids=None, live=True, filter="India"):
    date = (DAY + timedelta(days=offset)).isoformat()
    ids = ["a", "b"] if ids is None else ids
    return {
        "mode": "shadow_only", "checkedAt": date,
        "scans": [{
            "employer": "Deloitte South Asia", "filter": filter,
            "complete": complete, "status": "ok" if complete else "partial",
            "pagesRead": 1, "ids": ids[:], "totalReported": len(ids),
        }],
        "summary": {"verifiedNew": ([{
            "company": "Deloitte South Asia", "title": "Analyst Software",
            "jobUrl": "https://southasiacareers.deloitte.com/job/Analyst/123456789/",
            "state": "live" if live else "unconfirmed", "evidence": EVIDENCE,
            "country": "IN", "alreadyPublished": False,
        }] if offset == 2 else [])},
    }


class GateTests(unittest.TestCase):
    def test_three_complete_days_only_enable_candidates_not_publishing(self):
        reports = [run(i) for i in range(3)]
        out = inspect_history(reports, now=DAY.astimezone(timezone.utc)+timedelta(days=2, hours=1))
        self.assertEqual(len(out["publicationCandidates"]), 1)
        self.assertEqual(out["employers"]["Deloitte South Asia"]["status"], "eligible_for_further_checks")
        self.assertFalse(out["safeToEnableAutomaticPublishing"])

    def test_same_day_runs_do_not_pass(self):
        reports = [run(0) for _ in range(3)]
        out = inspect_history(reports, now=DAY.astimezone(timezone.utc))
        self.assertEqual(len(out["publicationCandidates"]), 0)

    def test_partial_scan_fails_closed(self):
        reports = [run(0), run(1,complete=False), run(2)]
        out = inspect_history(reports, now=DAY.astimezone(timezone.utc)+timedelta(days=2))
        self.assertEqual(out["employers"]["Deloitte South Asia"]["status"],"blocked")
        self.assertEqual(out["expiryDecisions"],[])

    def test_missing_twice_is_review_only(self):
        reports=[run(0,ids=["a","b","c"]),run(1,ids=["b","c"]),run(2,ids=["b","c"])]
        out=inspect_history(reports,now=DAY.astimezone(timezone.utc)+timedelta(days=2))
        self.assertEqual(len(out["expiryDecisions"]),1)
        self.assertEqual(out["expiryDecisions"][0]["action"],"verify_closure")
        self.assertFalse(out["safeToEnableAutomaticPublishing"])

    def test_listing_scope_cannot_change(self):
        reports=[run(0),run(1,filter="other"),run(2)]
        out=inspect_history(reports,now=DAY.astimezone(timezone.utc)+timedelta(days=2))
        self.assertEqual(out["employers"]["Deloitte South Asia"]["status"],"blocked")

    def test_evidence_is_exact_and_country_specific(self):
        reports=[run(0),run(1),run(2)]
        reports[-1]["summary"]["verifiedNew"][0]["evidence"]=["title-match","apply-control"]
        out=inspect_history(reports,now=DAY.astimezone(timezone.utc)+timedelta(days=2))
        self.assertEqual(out["publicationCandidates"],[])
        reports[-1]["summary"]["verifiedNew"][0]["evidence"]=EVIDENCE
        reports[-1]["summary"]["verifiedNew"][0]["country"]="unconfirmed"
        out=inspect_history(reports,now=DAY.astimezone(timezone.utc)+timedelta(days=2))
        self.assertEqual(out["publicationCandidates"],[])

    def test_large_listing_drop_is_blocked(self):
        reports=[run(0,ids=["a","b","c","d","e","f"]),run(1,ids=["a","b"]),run(2,ids=["a","b"])]
        out=inspect_history(reports,now=DAY.astimezone(timezone.utc)+timedelta(days=2))
        self.assertEqual(out["employers"]["Deloitte South Asia"]["status"],"blocked")

    def test_rejects_mutating_report_and_naive_timestamps(self):
        reports=[run(0),run(1),run(2)]
        reports[1]["mode"]="write"
        with self.assertRaises(ValueError):
            inspect_history(reports,now=DAY.astimezone(timezone.utc)+timedelta(days=2))
        reports[1]["mode"]="shadow_only"
        reports[1]["checkedAt"]="2026-10-10T03:00:00"
        with self.assertRaises(ValueError):
            inspect_history(reports,now=DAY.astimezone(timezone.utc)+timedelta(days=2))


if __name__=="__main__":
    unittest.main()
