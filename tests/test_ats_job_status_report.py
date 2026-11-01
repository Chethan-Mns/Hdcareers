"""Read-only owner report tests: exact ATS liveness, duplicates and safe rendering."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from ats_job_status_report import (duplicate_verdict, expand_sources, inspect,
                                   write_csv, write_html)


def candidate(id="ats-test", url="https://jobs.lever.co/acme/123",
              company="Acme", role="Graduate Trainee", loc="Bengaluru"):
    return {"id": id, "company": company, "role": role, "loc": loc,
            "apply": url, "externalId": "123", "sourceProvider": "lever",
            "sourceBoard": "acme", "eligibilityStatus": "needs_manual_verification",
            "reviewedStatus": "unreviewed"}


def report(items):
    return {"mode": "shadow_only", "profile": "fresher",
            "publicationAllowed": False, "expiryDecisionsAllowed": False,
            "candidateCount": len(items), "candidates": items, "scans": []}


class StatusReportTests(unittest.TestCase):
    def test_exact_published_url_is_duplicate_even_query_differs(self):
        c = candidate()
        records = expand_sources([{"company": "Acme", "role": "Graduate Trainee",
                                   "apply": c["apply"] + "?utm_source=ad"}], {}, [], [])
        self.assertEqual(duplicate_verdict(c, records)[0], "Duplicate")

    def test_duplicate_in_submitted_batch_and_review_queue(self):
        c = candidate()
        batch = {"priority": [{"job": {"company": "Acme",
                    "role": "Graduate Trainee", "apply": c["apply"]}}], "backup": []}
        records = expand_sources([], batch, [], [])
        self.assertEqual(duplicate_verdict(c, records)[0], "Duplicate")
        queue = [{"job": {"company": "Acme", "role": "Graduate Trainee", "apply": c["apply"]}}]
        self.assertEqual(duplicate_verdict(c, expand_sources([], {}, queue, []))[0], "Duplicate")

    def test_duplicate_from_earlier_draft(self):
        c = candidate()
        self.assertEqual(duplicate_verdict(
            c, expand_sources([], {}, [], [{"apply": c["apply"], "company": "Acme"}]))[0],
            "Duplicate")

    def test_same_role_other_job_id_only_possible_duplicate(self):
        c = candidate()
        other = {"company": "Acme", "role": "Graduate Trainee",
                 "loc": "Bengaluru", "apply": "https://jobs.lever.co/acme/999"}
        result = duplicate_verdict(c, expand_sources([other], {}, [], []))
        self.assertEqual(result[0], "Possible Duplicate")

    def test_other_location_not_automatically_duplicate(self):
        c = candidate()
        other = {"company": "Acme", "role": "Graduate Trainee",
                 "loc": "Hyderabad", "apply": "https://jobs.lever.co/acme/999"}
        self.assertEqual(duplicate_verdict(c, expand_sources([other], {}, [], []))[0], "New")

    def test_history_previously_seen_has_separate_verdict(self):
        c = candidate()
        hist = {"jobs": {c["id"]: {"apply": c["apply"]}}}
        self.assertEqual(duplicate_verdict(c, [], hist)[0], "Previously Seen")

    def test_live_and_expired_are_independent_of_duplicate_status(self):
        a, b, c = candidate(), candidate("other", "https://jobs.lever.co/beta/456", "Beta"), candidate(
            "third", "https://jobs.lever.co/gamma/789", "Gamma")
        states = {"Acme": ("active", "Official inventory exact role present"),
                  "Beta": ("expired", "Official exact posting says inactive"),
                  "Gamma": ("review", "HTTP 404 is not definitive closure")}
        result = inspect(report([a,b,c]), published=[{"apply": a["apply"]}], batch={},
                         queue=[], drafts=[], verifier=lambda x: states[x["company"]])
        self.assertEqual([r["availability"] for r in result["rows"]],
                         ["Live", "Expired", "Needs Review"])
        self.assertEqual([r["duplicate"] for r in result["rows"]],
                         ["Duplicate", "New", "New"])
        self.assertFalse(result["publicationAllowed"])
        self.assertFalse(result["expiryDecisionsAllowed"])
        self.assertTrue(all(not r["eligibleForPublishing"] for r in result["rows"]))

    def test_budget_remaining_jobs_are_review_not_false_live(self):
        a, b = candidate(), candidate("other", "https://jobs.lever.co/beta/456", "Beta")
        calls = []
        def verifier(x):
            calls.append(x)
            return ("active", "found")
        result = inspect(report([a,b]), published=[], batch={}, queue=[], drafts=[],
                         verifier=verifier, max_verify=1)
        self.assertEqual(len(calls), 1)
        self.assertEqual([r["availability"] for r in result["rows"]],
                         ["Live", "Needs Review"])

    def test_scanner_exclusions_reported_with_no_fake_liveness(self):
        a = report([candidate()])
        a["excludedCandidates"] = [{"company": "Already", "role": "Intern",
                                    "apply": "https://jobs.lever.co/other/111",
                                    "duplicateReason": "site"}]
        res = inspect(a, published=[], batch={}, queue=[], drafts=[],
                      verifier=lambda x: ("active", "present"))
        self.assertEqual(len(res["rows"]), 2)
        self.assertEqual(res["rows"][1]["duplicate"], "Duplicate")
        self.assertEqual(res["rows"][1]["availability"], "Needs Review")

    def test_fail_closed_wrong_profile_or_authority(self):
        for key, value in [("profile", "data-engineer-2y"), ("publicationAllowed", True),
                           ("expiryDecisionsAllowed", True), ("mode", "publish")]:
            d = report([candidate()])
            d[key] = value
            with self.assertRaises(ValueError):
                inspect(d, published=[], batch={}, queue=[], drafts=[],
                        verifier=lambda x: ("active", "yes"))

    def test_html_escapes_untrusted_posting_titles_and_valid_csv(self):
        c = candidate(role="<script>alert('x')</script>")
        result = inspect(report([c]), published=[], batch={}, queue=[], drafts=[],
                         verifier=lambda x: ("review", "Needs human review"))
        with tempfile.TemporaryDirectory() as folder:
            hp, cp = Path(folder)/"view.html", Path(folder)/"jobs.csv"
            write_html(hp, result)
            write_csv(cp, result["rows"])
            page = hp.read_text()
            self.assertNotIn("<script>alert('x')</script>", page)
            self.assertIn("&lt;script&gt;", page)
            self.assertIn("HD Careers", page)
            self.assertIn("company,role,location", cp.read_text(encoding="utf-8-sig"))

    def test_invalid_url_not_new(self):
        self.assertEqual(duplicate_verdict(candidate(url="http://localhost/"), [])[0],
                         "Needs Review")


if __name__ == "__main__":
    unittest.main()
