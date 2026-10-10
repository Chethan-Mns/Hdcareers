import json
import sys
import tempfile
import unittest
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from job_verifier_v2 import Evidence, Verdict
import job_radar_v3 as v3

NOW = datetime(2026, 10, 10, 4, 30, tzinfo=timezone.utc)
SOURCE = "greenhouse:example"


def gh_job(n, tenant="example"):
    return v3.make_job("greenhouse", tenant, str(n), f"Software Engineer Intern {n}",
                       f"https://job-boards.greenhouse.io/{tenant}/jobs/{n}", "India")


def snap(jobs, source=SOURCE, ok=True, reason="test"):
    return {"source": source, "ok": ok, "reason": reason, "url": "https://boards-api.greenhouse.io/v1/boards/example/jobs", "jobs": jobs}


def verdict(job, state="LIVE", polarity="open", code="greenhouse.apply_form", exact=True):
    rid = job["requisitionId"] if exact else "WRONG_ID"
    e = Evidence(job["provider"], "shadow-fixture", "provider", "A", v3.iso(NOW),
                 job["requisitionId"], rid, "exact" if exact else "mismatch",
                 polarity, code, job["url"])
    return Verdict(state, "test_fixture", job["provider"], job["requisitionId"],
                   v3.iso(NOW), v3.iso(NOW + timedelta(minutes=30)), ["fixture"], [e])


class InventoryTests(unittest.TestCase):
    def test_greenhouse_and_exact_ids(self):
        items = v3.parse_inventory("greenhouse", "acme", {"jobs": [
            {"id": 123, "title": "Graduate Developer", "location": {"name": "Bengaluru"}},
            {"id": 123, "title": "Duplicate", "location": {}}]})
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["key"], "greenhouse:acme:123")
        self.assertEqual(items[0]["location"], "Bengaluru")

    def test_lever_and_ashby(self):
        l = v3.parse_inventory("lever", "test", [{"id": "a-b", "text": "Graduate Software Developer",
           "categories": {"location": "Mumbai"}}])
        self.assertEqual(l[0]["url"], "https://jobs.lever.co/test/a-b")
        a = v3.parse_inventory("ashby", "xyz", {"jobs": [{"title": "Intern", "jobUrl": "https://jobs.ashbyhq.com/xyz/99"},
           {"title": "Unlisted", "isListed": False, "jobUrl": "https://jobs.ashbyhq.com/xyz/88"}]})
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0]["key"], "ashby:xyz:99")

    def test_rejects_truncated_or_wrong_tenant(self):
        with self.assertRaises(ValueError):
            v3.parse_inventory("greenhouse", "acme", {"error": "blocked"})
        with self.assertRaises(ValueError):
            v3.parse_inventory("ashby", "acme", [{"jobUrl": "https://jobs.ashbyhq.com/evil/99", "title": "Intern"}])
        with self.assertRaises(ValueError):
            v3.inventory_endpoint("lever", "../evil")

    def test_api_failure_fails_closed(self):
        with patch.object(v3, "fetch_json", side_effect=TimeoutError("slow")):
            result = v3.collect_inventory("greenhouse", "acme")
        self.assertFalse(result["ok"])
        self.assertEqual(result["jobs"], [])


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.state = v3.state_template()
        self.jobs = [gh_job(n) for n in range(100, 108)]
        self.assertTrue(v3.observe_snapshot(self.state, snap(self.jobs), NOW)["accepted"])

    def test_missing_once_does_not_expire(self):
        one = v3.observe_snapshot(self.state, snap(self.jobs[1:]), NOW + timedelta(minutes=20))
        self.assertTrue(one["accepted"])
        self.assertEqual(one["missing"], 1)
        hist = self.state["jobs"][self.jobs[0]["key"]]
        self.assertEqual(hist["lifecycle"], "CLOSURE_SUSPECTED")
        self.assertEqual(hist["verification"], "UNCONFIRMED")
        v3.observe_snapshot(self.state, snap(self.jobs[1:]), NOW + timedelta(minutes=45))
        # Only the previous snapshot is compared; no false expiry from missing inventory.
        self.assertNotEqual(hist["lifecycle"], "EXPIRED")

    def test_implausible_inventory_drop_is_ignored(self):
        bad = v3.observe_snapshot(self.state, snap(self.jobs[:1]), NOW + timedelta(minutes=20))
        self.assertFalse(bad["accepted"])
        self.assertEqual(bad["reason"], "anomalous_inventory_drop")
        self.assertEqual(self.state["jobs"][self.jobs[1]["key"]]["missingStreak"], 0)

    def test_api_outage_does_not_change_history(self):
        bad = v3.observe_snapshot(self.state, snap([], ok=False, reason="HTTP 403"), NOW + timedelta(minutes=20))
        self.assertFalse(bad["accepted"])
        self.assertEqual(self.state["jobs"][self.jobs[0]["key"]]["missingStreak"], 0)

    def test_api_404_cannot_expire_even_repeated(self):
        j = self.jobs[0]
        hist = self.state["jobs"][j["key"]]
        v = asdict(verdict(j, "EXPIRED", "closed", "greenhouse.api_404"))
        for step in (1, 20, 40):
            v3.apply_verification(hist, v, NOW + timedelta(minutes=step), present=False)
        self.assertNotEqual(hist["lifecycle"], "EXPIRED")
        self.assertEqual(hist["verification"], "UNCONFIRMED")

    def test_explicit_closure_requires_two_observations_spaced_apart(self):
        j = v3.make_job("workday", "acme", "R-1", "Graduate", "https://acme.example.com/job/R-1")
        hist = v3.ensure_history(self.state, j, NOW)
        v = asdict(verdict(j, "EXPIRED", "closed", "workday.can_apply_false"))
        self.assertEqual(v3.apply_verification(hist, v, NOW, False), "CLOSURE_SUSPECTED")
        self.assertEqual(v3.apply_verification(hist, v, NOW + timedelta(minutes=5), False), "CLOSURE_SUSPECTED")
        self.assertEqual(v3.apply_verification(hist, v, NOW + timedelta(minutes=20), False), "EXPIRED")

    def test_conflicting_open_and_closed_never_auto_expire(self):
        j = v3.make_job("workday", "acme", "R-2", "Graduate", "https://acme.example.com/job/R-2")
        hist = v3.ensure_history(self.state, j, NOW)
        v = asdict(verdict(j, "EXPIRED", "closed", "workday.can_apply_false"))
        v["evidence"].append(asdict(verdict(j).evidence[0]))
        for minutes in (0, 25):
            v3.apply_verification(hist, v, NOW + timedelta(minutes=minutes), False)
        self.assertNotEqual(hist["lifecycle"], "EXPIRED")

    def test_live_must_be_exact_and_current(self):
        j = self.jobs[0]
        hist = self.state["jobs"][j["key"]]
        v3.apply_verification(hist, asdict(verdict(j, "LIVE", exact=False)), NOW, True)
        self.assertFalse(v3.eligible_for_publish(hist, NOW))
        v3.apply_verification(hist, asdict(verdict(j)), NOW, True)
        self.assertTrue(v3.eligible_for_publish(hist, NOW + timedelta(minutes=25)))
        self.assertFalse(v3.eligible_for_publish(hist, NOW + timedelta(minutes=31)))

    def test_missing_or_unknown_does_not_keep_stale_live_eligible(self):
        j = self.jobs[0]
        hist = self.state["jobs"][j["key"]]
        v3.apply_verification(hist, asdict(verdict(j)), NOW, True)
        v3.observe_snapshot(self.state, snap(self.jobs[1:]), NOW + timedelta(minutes=10))
        self.assertFalse(v3.eligible_for_publish(hist, NOW + timedelta(minutes=10)))

    def test_reappearing_job_is_not_considered_verified_again(self):
        j = self.jobs[0]
        hist = self.state["jobs"][j["key"]]
        v3.apply_verification(hist, asdict(verdict(j)), NOW, True)
        v3.observe_snapshot(self.state, snap(self.jobs[1:]), NOW + timedelta(minutes=10))
        v3.observe_snapshot(self.state, snap(self.jobs), NOW + timedelta(minutes=20))
        self.assertFalse(v3.eligible_for_publish(hist, NOW + timedelta(minutes=20)))
        self.assertEqual(hist["lifecycle"], "RECHECK_REQUIRED")

    def test_top10_live_only_two_per_employer(self):
        later = NOW + timedelta(minutes=3)
        for j in self.jobs:
            v3.apply_verification(self.state["jobs"][j["key"]], asdict(verdict(j)), later, True)
        self.assertEqual(len(v3.select_top(self.state, later, count=10)), 2)

    def test_snapshot_survives_restart(self):
        with tempfile.TemporaryDirectory() as t:
            file = Path(t) / "state.json"
            file.write_text(json.dumps(self.state))
            new = v3.load_state(file)
        self.assertEqual(len(new["jobs"]), 8)

    def test_run_shadow_never_posts_or_deploys(self):
        source = [{"provider": "greenhouse", "tenant": "example"}]
        result_state, report = v3.run_shadow(source, v3.state_template(), NOW, max_verify=2,
            verifier=lambda url: verdict(self.jobs[0]),
            snapshots=[snap([self.jobs[0]])])
        self.assertTrue(report["shadow"])
        self.assertFalse(report["productionWrites"])
        self.assertFalse(report["websiteDeploy"])
        self.assertFalse(report["telegramPosts"])
        self.assertEqual(report["verified"], 1)
        self.assertEqual(len(report["topEligible"]), 1)

    def test_missing_job_rechecked_but_not_falsely_expired(self):
        initial = v3.state_template()
        v3.observe_snapshot(initial, snap(self.jobs), NOW)
        report = v3.run_shadow([{"provider": "greenhouse", "tenant": "example"}], initial,
            NOW + timedelta(minutes=20), max_verify=4,
            verifier=lambda url: verdict(self.jobs[0], "EXPIRED", "closed", "greenhouse.api_404"),
            snapshots=[snap(self.jobs[1:])])[1]
        self.assertTrue(any(not c["present"] for c in report["checks"]))
        self.assertEqual(report["lifecycleCounts"].get("EXPIRED", 0), 0)


if __name__ == "__main__":
    unittest.main()
