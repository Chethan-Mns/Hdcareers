import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from job_verifier_v2 import ProviderRef, Evidence, decide, resolve, verify_url

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)

class V2Tests(unittest.TestCase):
    def test_resolves_greenhouse(self):
        r = resolve("https://job-boards.greenhouse.io/cloudsek/jobs/12345")
        self.assertEqual((r.provider, r.tenant, r.requisition_id), ("greenhouse", "cloudsek", "12345"))

    def test_resolves_lever(self):
        r = resolve("https://jobs.lever.co/acme/abc-123")
        self.assertEqual((r.provider, r.tenant, r.requisition_id), ("lever", "acme", "abc-123"))

    def test_resolves_smartrecruiters(self):
        r = resolve("https://jobs.smartrecruiters.com/AristaNetworks/744000152369329-software-engineer-intern")
        self.assertEqual((r.provider, r.tenant, r.requisition_id), ("smartrecruiters", "AristaNetworks", "744000152369329"))

    def test_resolves_ashby(self):
        r = resolve("https://jobs.ashbyhq.com/kognitos/a3c5bd4c-f6fb-4eb0-b943-e0e1a1d878c5")
        self.assertEqual((r.provider, r.tenant, r.requisition_id), ("ashby", "kognitos", "a3c5bd4c-f6fb-4eb0-b943-e0e1a1d878c5"))

    def test_resolves_workday(self):
        r = resolve("https://redhat.wd5.myworkdayjobs.com/en-US/Jobs/job/Software-Engineering-Intern_R-058560")
        self.assertEqual((r.provider, r.tenant, r.requisition_id), ("workday", "redhat", "R-058560"))

    def test_resolves_oracle_hcm(self):
        r = resolve("https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/jobsearch/job/344317")
        self.assertEqual((r.provider, r.tenant, r.requisition_id), ("oracle_hcm", "eeho.fa.us2.oraclecloud.com|jobsearch", "344317"))

    def test_oracle_hcm_is_review_only_even_with_open_flow(self):
        ref = ProviderRef("oracle_hcm", "example.oraclecloud.com|CX_1", "123", "https://example.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/123")
        e = Evidence("oracle_hcm", "oracle_hcm-v1", "browser", "A", NOW.isoformat(), "123", "123", "exact", "open", "oracle.application_flow", ref.source_url)
        v = decide(ref, [e], NOW)
        self.assertEqual(v.state, "UNCONFIRMED")
        self.assertIn("provider_review_only", v.reasons)

    def test_unknown_provider_is_unconfirmed(self):
        self.assertEqual(verify_url("https://careers.example.com/jobs/1", NOW).state, "UNCONFIRMED")

    def test_tier_b_inventory_alone_cannot_make_live(self):
        ref = ProviderRef("greenhouse", "acme", "123", "https://job-boards.greenhouse.io/acme/jobs/123")
        e = Evidence("greenhouse", "greenhouse-v1", "api", "B", NOW.isoformat(), "123", "123", "exact", "open", "greenhouse.exact_record", "https://api.example")
        self.assertEqual(decide(ref, [e], NOW).state, "UNCONFIRMED")

    def test_exact_tier_a_apply_form_makes_live(self):
        ref = ProviderRef("lever", "acme", "abc", "https://jobs.lever.co/acme/abc")
        e = Evidence("lever", "lever-v1", "http", "A", NOW.isoformat(), "abc", "abc", "exact", "open", "lever.apply_form", ref.source_url)
        v = decide(ref, [e], NOW)
        self.assertEqual(v.state, "LIVE")
        self.assertIsNotNone(v.valid_until)

    def test_exact_tier_a_closed_makes_expired(self):
        ref = ProviderRef("lever", "acme", "abc", "https://jobs.lever.co/acme/abc")
        e = Evidence("lever", "lever-v1", "http", "A", NOW.isoformat(), "abc", "abc", "exact", "closed", "lever.apply_closed", ref.source_url)
        self.assertEqual(decide(ref, [e], NOW).state, "EXPIRED")

    def test_conflicting_tier_a_is_unconfirmed(self):
        ref = ProviderRef("lever", "acme", "abc", "https://jobs.lever.co/acme/abc")
        a = Evidence("lever", "lever-v1", "http", "A", NOW.isoformat(), "abc", "abc", "exact", "open", "lever.apply_form", ref.source_url)
        b = Evidence("lever", "lever-v1", "api", "A", NOW.isoformat(), "abc", "abc", "exact", "closed", "lever.api_404", ref.source_url)
        self.assertEqual(decide(ref, [a, b], NOW).state, "UNCONFIRMED")

    def test_review_only_provider_cannot_become_live(self):
        ref = ProviderRef("workday", "acme", "R-1", "https://acme.wd5.myworkdayjobs.com/en-US/jobs/job/Test_R-1")
        e = Evidence("workday", "workday-v1", "browser", "A", NOW.isoformat(), "R-1", "R-1", "exact", "open", "workday.application_flow", ref.source_url)
        v = decide(ref, [e], NOW)
        self.assertEqual(v.state, "UNCONFIRMED")
        self.assertIn("provider_review_only", v.reasons)

    @patch("job_verifier_v2.fetch_html")
    @patch("job_verifier_v2.fetch_json")
    def test_greenhouse_requires_application_form(self, fj, fh):
        fj.return_value = (200, "https://boards-api.greenhouse.io/v1/boards/acme/jobs/123", {}, {"id": 123, "absolute_url": "https://job-boards.greenhouse.io/acme/jobs/123"})
        fh.return_value = (200, "https://job-boards.greenhouse.io/acme/jobs/123", {}, "<h1>Job</h1>")
        self.assertEqual(verify_url("https://job-boards.greenhouse.io/acme/jobs/123", NOW).state, "UNCONFIRMED")
        fh.return_value = (200, "https://job-boards.greenhouse.io/acme/jobs/123", {}, '<form action="/123">Submit application</form>')
        self.assertEqual(verify_url("https://job-boards.greenhouse.io/acme/jobs/123", NOW).state, "LIVE")

    @patch("job_verifier_v2.fetch_html")
    @patch("job_verifier_v2.fetch_json")
    def test_lever_dead_apply_destination_beats_inventory(self, fj, fh):
        fj.return_value = (200, "https://api.lever.co/v0/postings/acme/abc", {}, {"id": "abc", "applyUrl": "https://jobs.lever.co/acme/abc/apply"})
        fh.return_value = (200, "https://jobs.lever.co/acme/abc/apply", {}, "<main>This position is no longer posted</main>")
        self.assertEqual(verify_url("https://jobs.lever.co/acme/abc", NOW).state, "EXPIRED")

    @patch("job_verifier_v2.fetch_json")
    def test_greenhouse_api_404_is_expired(self, fj):
        fj.side_effect = HTTPError("x", 404, "Not found", {}, None)
        self.assertEqual(verify_url("https://job-boards.greenhouse.io/acme/jobs/123", NOW).state, "EXPIRED")

    @patch("job_verifier_v2.smartrecruiters_browser_probe")
    @patch("job_verifier_v2.fetch_json")
    def test_smartrecruiters_application_form_is_live(self, fj, bp):
        fj.return_value = (200, "https://api.smartrecruiters.com/v1/companies/Acme/postings/123", {}, {"id": "123", "active": True, "applyUrl": "https://jobs.smartrecruiters.com/Acme/123-role?oga=true"})
        bp.return_value = ("open", "https://jobs.smartrecruiters.com/Acme/123-role?oga=true", "")
        self.assertEqual(verify_url("https://jobs.smartrecruiters.com/Acme/123-role", NOW).state, "LIVE")

    @patch("job_verifier_v2.smartrecruiters_browser_probe")
    @patch("job_verifier_v2.fetch_json")
    def test_smartrecruiters_api_alone_cannot_make_live(self, fj, bp):
        fj.return_value = (200, "https://api.smartrecruiters.com/v1/companies/Acme/postings/123", {}, {"id": "123", "active": True})
        bp.return_value = ("neutral", "https://jobs.smartrecruiters.com/Acme/123-role", "")
        self.assertEqual(verify_url("https://jobs.smartrecruiters.com/Acme/123-role", NOW).state, "UNCONFIRMED")

    @patch("job_verifier_v2.fetch_json")
    def test_smartrecruiters_filled_text_is_expired(self, fj):
        fj.return_value = (200, "https://api.smartrecruiters.com/v1/companies/Acme/postings/123", {}, {"id": "123", "active": True, "jobAd": {"sections": {"additionalInformation": {"text": "position has been filled."}}}})
        self.assertEqual(verify_url("https://jobs.smartrecruiters.com/Acme/123-role", NOW).state, "EXPIRED")

    @patch("job_verifier_v2.fetch_json")
    def test_smartrecruiters_404_is_expired(self, fj):
        fj.side_effect = HTTPError("x", 404, "Not found", {}, None)
        self.assertEqual(verify_url("https://jobs.smartrecruiters.com/Acme/123-role", NOW).state, "EXPIRED")

    @patch("job_verifier_v2.fetch_html")
    @patch("job_verifier_v2.fetch_json")
    def test_ashby_apply_form_is_live(self, fj, fh):
        rid = "a3c5bd4c-f6fb-4eb0-b943-e0e1a1d878c5"
        fj.return_value = (200, "https://api.ashbyhq.com/posting-api/job-board/acme", {}, {"jobs": [{"jobUrl": f"https://jobs.ashbyhq.com/acme/{rid}", "applyUrl": f"https://jobs.ashbyhq.com/acme/{rid}/application"}]})
        fh.return_value = (200, f"https://jobs.ashbyhq.com/acme/{rid}/application", {}, f'<form action="/{rid}">Submit application</form>')
        self.assertEqual(verify_url(f"https://jobs.ashbyhq.com/acme/{rid}", NOW).state, "LIVE")

    @patch("job_verifier_v2.fetch_json")
    def test_ashby_absent_current_board_is_expired(self, fj):
        rid = "a3c5bd4c-f6fb-4eb0-b943-e0e1a1d878c5"
        fj.return_value = (200, "https://api.ashbyhq.com/posting-api/job-board/acme", {}, {"jobs": []})
        self.assertEqual(verify_url(f"https://jobs.ashbyhq.com/acme/{rid}", NOW).state, "EXPIRED")

    @patch("job_verifier_v2.workday_browser_probe")
    @patch("job_verifier_v2.fetch_json")
    def test_workday_can_apply_false_is_expired(self, fj, bp):
        fj.return_value = (200, "https://redhat.wd5.myworkdayjobs.com/x", {}, {"jobPostingInfo": {"jobReqId": "R-058560", "canApply": False}})
        bp.return_value = ("neutral", "https://redhat.wd5.myworkdayjobs.com/x", "")
        self.assertEqual(verify_url("https://redhat.wd5.myworkdayjobs.com/en-US/Jobs/job/Software-Engineering-Intern_R-058560", NOW).state, "EXPIRED")

    @patch("job_verifier_v2.workday_browser_probe")
    @patch("job_verifier_v2.fetch_json")
    def test_workday_can_apply_true_stays_review_only(self, fj, bp):
        fj.return_value = (200, "https://redhat.wd5.myworkdayjobs.com/x", {}, {"jobPostingInfo": {"jobReqId": "R-058560", "canApply": True}})
        bp.return_value = ("open", "https://redhat.wd5.myworkdayjobs.com/application", "Create Account")
        v = verify_url("https://redhat.wd5.myworkdayjobs.com/en-US/Jobs/job/Software-Engineering-Intern_R-058560", NOW)
        self.assertEqual(v.state, "UNCONFIRMED")
        self.assertIn("provider_review_only", v.reasons)

    @patch("job_verifier_v2.workday_browser_probe")
    @patch("job_verifier_v2.fetch_json")
    def test_workday_cxs_alone_cannot_make_live(self, fj, bp):
        fj.return_value = (200, "https://redhat.wd5.myworkdayjobs.com/x", {}, {"jobPostingInfo": {"jobReqId": "R-058560"}})
        bp.return_value = ("neutral", "https://redhat.wd5.myworkdayjobs.com/x", "")
        self.assertEqual(verify_url("https://redhat.wd5.myworkdayjobs.com/en-US/Jobs/job/Software-Engineering-Intern_R-058560", NOW).state, "UNCONFIRMED")

    @patch("job_verifier_v2.workday_browser_probe")
    @patch("job_verifier_v2.fetch_json")
    def test_workday_generic_application_flow_cannot_make_live(self, fj, bp):
        fj.return_value = (200, "https://redhat.wd5.myworkdayjobs.com/x", {}, {"jobPostingInfo": {"jobReqId": "R-058560"}})
        bp.return_value = ("open", "https://redhat.wd5.myworkdayjobs.com/application", "Create Account")
        self.assertEqual(verify_url("https://redhat.wd5.myworkdayjobs.com/en-US/Jobs/job/Software-Engineering-Intern_R-058560", NOW).state, "UNCONFIRMED")

    @patch("job_verifier_v2.workday_browser_probe")
    @patch("job_verifier_v2.fetch_json")
    def test_workday_browser_closed_beats_stale_cxs(self, fj, bp):
        fj.return_value = (200, "https://marmon.wd501.myworkdayjobs.com/x", {}, {"jobPostingInfo": {"jobReqId": "JR0000043944"}})
        bp.return_value = ("closed", "https://marmon.wd501.myworkdayjobs.com/x", "position has been filled")
        self.assertEqual(verify_url("https://marmon.wd501.myworkdayjobs.com/en-US/Marmon_Careers/job/Karnataka-IN/Graduate-Engineer-Trainee_JR0000043944", NOW).state, "EXPIRED")

if __name__ == "__main__":
    unittest.main()
