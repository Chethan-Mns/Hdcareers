"""Persistent history never promotes, publishes or expires discovered ATS jobs."""
import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from ats_discovery_history import empty_history, update_history


def fixture(time="2026-11-01T06:19:42+00:00", candidates=True, complete=True):
    return {
        "profile": "fresher", "mode": "shadow_only",
        "generatedAt": time,
        "publicationAllowed": False, "expiryDecisionsAllowed": False,
        "candidateCount": int(candidates), "scannedBoards": 1,
        "scans": [{"provider": "greenhouse", "board": "acme",
                   "company": "Acme", "status": "ok" if complete else "partial",
                   "complete": complete, "notes": [], "newReviewCandidates": int(candidates)}],
        "candidates": ([{
            "id": "ats-abc", "company": "Acme", "role": "Graduate Engineer Trainee",
            "loc": "Bengaluru, India", "apply": "https://job-boards.greenhouse.io/acme/jobs/112",
            "externalId": "112", "sourceProvider": "greenhouse", "sourceBoard": "acme",
            "eligibilityStatus": "needs_manual_verification", "reviewedStatus": "unreviewed",
        }] if candidates else []),
    }


class HistoryTests(unittest.TestCase):
    def test_first_discovery_and_second_reobservation(self):
        original = empty_history()
        original_copy = deepcopy(original)
        report = fixture()
        state, first, repeat = update_history(original, report)
        self.assertEqual(first, ["ats-abc"])
        self.assertEqual(repeat, [])
        self.assertEqual(original, original_copy)
        record = state["jobs"]["ats-abc"]
        self.assertFalse(record["eligibleForPublishing"])
        self.assertFalse(record["expired"])
        self.assertEqual(record["firstSeenAt"], report["generatedAt"])
        self.assertEqual(record["seenCount"], 1)

        second, first_again, repeated = update_history(
            state, fixture(time="2026-11-02T06:19:42+00:00"))
        self.assertEqual(first_again, [])
        self.assertEqual(repeated, ["ats-abc"])
        self.assertEqual(second["jobs"]["ats-abc"]["seenCount"], 2)
        self.assertEqual(second["jobs"]["ats-abc"]["firstSeenAt"], report["generatedAt"])

    def test_absence_on_complete_board_is_not_expiry(self):
        first, _, _ = update_history(empty_history(), fixture())
        second, _, _ = update_history(
            first, fixture(time="2026-11-02T06:19:42+00:00", candidates=False))
        record = second["jobs"]["ats-abc"]
        self.assertEqual(record["observationStatus"], "not_reobserved_needs_verification")
        self.assertFalse(record["expired"])
        self.assertFalse(record["eligibleForPublishing"])

    def test_partial_board_preserves_previous_observation(self):
        first, _, _ = update_history(empty_history(), fixture())
        second, _, _ = update_history(first, fixture(
            time="2026-11-02T06:19:42+00:00", candidates=False, complete=False))
        self.assertEqual(second["jobs"]["ats-abc"]["observationStatus"], "observed")
        self.assertEqual(second["boards"]["greenhouse|acme|acme"]["lastAttemptStatus"], "incomplete")

    def test_reappeared_job_does_not_reset_history(self):
        initial, _, _ = update_history(empty_history(), fixture())
        missing, _, _ = update_history(initial, fixture(
            time="2026-11-02T06:19:42+00:00", candidates=False))
        final, first, repeats = update_history(
            missing, fixture(time="2026-11-03T06:19:42+00:00"))
        self.assertFalse(first)
        self.assertEqual(repeats, ["ats-abc"])
        self.assertEqual(final["jobs"]["ats-abc"]["observationStatus"], "observed")
        self.assertEqual(final["jobs"]["ats-abc"]["seenCount"], 2)

    def test_personal_experience_and_unsafe_authority_disallowed(self):
        for key, value in [("profile", "data-engineer-2y"), ("publicationAllowed", True),
                           ("expiryDecisionsAllowed", True), ("mode", "publish")]:
            report = fixture()
            report[key] = value
            with self.assertRaises(ValueError, msg=key):
                update_history(empty_history(), report)

    def test_out_of_order_and_unknown_schema_refused(self):
        recent, _, _ = update_history(empty_history(), fixture(
            time="2026-11-03T06:19:42+00:00"))
        with self.assertRaises(ValueError):
            update_history(recent, fixture(time="2026-11-01T06:19:42+00:00"))
        with self.assertRaises(ValueError):
            update_history({"schemaVersion": 0}, fixture())

    def test_missing_candidate_fields_and_collisions_are_rejected(self):
        p = fixture()
        p["candidates"][0]["role"] = ""
        with self.assertRaises(ValueError):
            update_history(empty_history(), p)
        p = fixture()
        p["candidates"].append(dict(p["candidates"][0]))
        p["candidateCount"] = 2
        with self.assertRaises(ValueError):
            update_history(empty_history(), p)


if __name__ == "__main__":
    unittest.main()
