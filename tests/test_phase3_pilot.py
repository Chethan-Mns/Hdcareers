import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from phase3_pilot import build_report, source_candidate, source_grounded_draft, SITE, EMPLOYER

NOW = datetime(2026, 10, 14, tzinfo=timezone.utc)
PID = "3fd5cb37-6541-4e97-a827-d644468e6535"
URL = f"https://jobs.lever.co/{SITE}/{PID}"
RAW = {"id": PID, "hostedUrl": URL, "text": "MS - NOC Apprentice/Intern (6 months)",
       "descriptionPlain": "Help monitor and troubleshoot network operations under supervision",
       "categories": {"location": "India"},
       "lists": [{"text": "Responsibilities", "content": "<ul><li>Monitor network alerts</li></ul>"}]}

def positive(job, now=None):
    return {"id": job["id"], "url": job["apply"], "state": "active",
            "reason": "Lever public posting inventory contains the exact published job"}

class PilotTests(unittest.TestCase):
    def test_positive_end_to_end_dry_run(self):
        report = build_report([RAW], [], fetch=lambda url: RAW, verify=positive, now=NOW)
        self.assertEqual(report["summary"]["draftReady"], 1)
        item = report["candidates"][0]
        self.assertTrue(item["readyForDraftReview"])
        self.assertFalse(item["readyForPublishing"])
        self.assertEqual(report["summary"]["publishReady"], 0)
        self.assertEqual(item["facts"]["company"], EMPLOYER)
        self.assertIsNone(item["facts"]["salary"])
        self.assertFalse(report["autoPublishEnabled"])
        self.assertFalse(report["productionWrites"])
        self.assertEqual(report["websiteDeployments"], 0)
        self.assertEqual(report["telegramMessagesSent"], 0)

    def test_duplicate_discovered_or_previously_published_is_excluded(self):
        result = build_report([RAW, RAW], [{"apply": URL}], fetch=lambda url: RAW, verify=positive, now=NOW)
        self.assertEqual(result["summary"]["newCandidatesChecked"], 0)

    def test_bad_company_job_id_or_url_fails_closed(self):
        bad = [
            dict(RAW, id="not-a-uuid"),
            dict(RAW, hostedUrl="https://jobs.lever.co/other/" + PID),
            dict(RAW, hostedUrl="http://jobs.lever.co/" + SITE + "/" + PID),
            dict(RAW, hostedUrl="https://malicious.example/" + SITE + "/" + PID),
            dict(RAW, text="")
        ]
        for candidate in bad:
            with self.subTest(candidate=candidate):
                self.assertIsNone(source_candidate(candidate))

    def test_wrong_exact_id_title_or_url_holds_draft(self):
        c = source_candidate(RAW)
        for wrong in (dict(RAW, id="00000000-6541-4e97-a827-d644468e6535"),
                      dict(RAW, text="Some Other Role"),
                      dict(RAW, hostedUrl="https://jobs.lever.co/thinkahead/other")):
            self.assertEqual(source_grounded_draft(c, wrong)["state"], "hold")

    def test_missing_employer_facts_do_not_get_invented(self):
        c = source_candidate(RAW)
        result = source_grounded_draft(c, dict(RAW, descriptionPlain="", categories={}, lists=[]))
        self.assertEqual(result["state"], "hold")
        self.assertIsNone(result["facts"]["employerPostedAt"])
        self.assertIsNone(result["facts"]["salary"])

    def test_foreign_or_ambiguous_location_cannot_be_promoted_to_india_draft(self):
        c = source_candidate(RAW)
        for location in ("New York, United States", "Remote - USA", "Worldwide", "Remote", ""):
            with self.subTest(location=location):
                exact = dict(RAW, categories={"location": location})
                self.assertEqual(source_grounded_draft(c, exact)["state"], "hold")
        self.assertEqual(source_grounded_draft(c, RAW)["state"], "draft_ready")

    def test_403_timeout_wrong_check_and_expired_do_not_publish(self):
        for state in ("review", "expired", "active"):
            def checking(job, now=None):
                r = positive(job, now)
                r["state"] = state
                if state == "active":
                    r["url"] = "https://jobs.lever.co/other/" + PID
                return r
            result = build_report([RAW], [], fetch=lambda url: RAW, verify=checking, now=NOW)
            self.assertEqual(result["summary"]["draftReady"], 0)
        result = build_report([RAW], [], fetch=lambda url: (_ for _ in ()).throw(TimeoutError()), verify=positive, now=NOW)
        self.assertEqual(result["summary"]["draftReady"], 0)

    def test_discovery_list_failure_cannot_be_marked_complete(self):
        with self.assertRaises(ValueError):
            build_report({"error": "blocked"}, [], fetch=lambda url: RAW, verify=positive, now=NOW)

if __name__ == "__main__":
    unittest.main()
