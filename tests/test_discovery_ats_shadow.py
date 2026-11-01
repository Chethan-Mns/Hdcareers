"""Offline regressions for read-only official ATS discovery."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import discovery_ats_shadow as a


class BoardsTests(unittest.TestCase):
    def test_recovers_real_board_shapes_and_dedupes(self):
        existing = [
            {"company": "Test GH", "apply": "https://job-boards.greenhouse.io/testjobs/jobs/123"},
            {"company": "Test GH", "apply": "https://job-boards.greenhouse.io/testjobs/jobs/456?gh_src=ad"},
            {"company": "Test Lever", "apply": "https://jobs.lever.co/testlever/uuid-one"},
            {"company": "Test Ashby", "apply": "https://jobs.ashbyhq.com/testashby/uuid-two"},
            {"company": "Test Smart", "apply": "https://jobs.smartrecruiters.com/testsmart/123-title"},
            {"company": "Test Workday", "apply": "https://testwd.wd5.myworkdayjobs.com/en-US/External_Careers/job/India/Intern_R123"},
        ]
        boards = a.boards_from_jobs(existing)
        self.assertEqual(len(boards), 5)
        self.assertEqual({x["provider"] for x in boards}, a.SOURCE_PROVIDER)
        wd = next(x for x in boards if x["provider"] == "workday")
        self.assertEqual(wd["board"], "External_Careers")
        self.assertEqual(wd["tenant"], "testwd")

    def test_rejects_untrusted_urls(self):
        for url in ("http://jobs.lever.co/a/123", "https://evil.test/company/123",
                    "https://jobs.lever.co@evil.test/test/123",
                    "https://jobs.lever.co/a", "https://job-boards.greenhouse.io/a/notjobs/123",
                    "https://test.wd1.myworkdayjobs.com/a/notjob/123"):
            self.assertIsNone(a.parse_board("Fake", url), url)

    def test_source_filtering_avoids_experienced_and_nonindia(self):
        b = a.parse_board("Test", "https://jobs.lever.co/testboard/old-id")
        self.assertIsNone(a.normalize_posting(b, {"id": "1", "url": "https://jobs.lever.co/testboard/id1",
            "title": "Senior Software Engineer", "location": "Bengaluru", "description": ""}))
        self.assertIsNone(a.normalize_posting(b, {"id": "2", "url": "https://jobs.lever.co/testboard/id2",
            "title": "Software Engineering Intern", "location": "London, UK", "country": "GB", "description": ""}))
        self.assertIsNone(a.normalize_posting(b, {"id": "3", "url": "https://jobs.lever.co/evilboard/id3",
            "title": "Software Engineering Intern", "location": "Bengaluru", "description": ""}))
        item = a.normalize_posting(b, {"id": "4", "url": "https://jobs.lever.co/testboard/id4",
            "title": "Software Engineering Intern", "location": "Bengaluru", "description": "<p>Internship</p>"})
        self.assertEqual(item["reviewedStatus"], "unreviewed")
        self.assertEqual(item["eligibilityStatus"], "needs_manual_verification")
        self.assertEqual(item["sourceStatus"], "listed_on_official_ATS")

    def test_greenhouse_full_board_and_site_dedupe(self):
        site = [{"company": "Acme", "role": "Software Engineering Intern",
                 "apply": "https://job-boards.greenhouse.io/acme/jobs/11"}]
        def fake(url, body=None):
            self.assertIn("boards-api.greenhouse.io", url)
            return {"jobs": [
                {"id": 11, "title": "Software Engineering Intern", "absolute_url": site[0]["apply"],
                 "location": {"name": "Bengaluru"}, "content": "0-1 years experience"},
                {"id": 12, "title": "Graduate Engineer Trainee", "absolute_url": "https://job-boards.greenhouse.io/acme/jobs/12",
                 "location": {"name": "Hyderabad"}, "content": "<p>0-2 years experience</p>"},
                {"id": 13, "title": "Senior Engineer", "absolute_url": "https://job-boards.greenhouse.io/acme/jobs/13",
                 "location": {"name": "Hyderabad"}, "content": "5+ years experience"},
            ]}
        result = a.discover(site, fetcher=fake)
        self.assertEqual(result["mode"], "shadow_only")
        self.assertEqual(result["candidateCount"], 1)
        self.assertEqual(result["scans"][0]["duplicateOnSite"], 1)
        self.assertTrue(result["scans"][0]["complete"])
        self.assertFalse(result["publicationAllowed"])
        self.assertFalse(result["expiryDecisionsAllowed"])
        self.assertEqual(result["candidates"][0]["role"], "Graduate Engineer Trainee")

    def test_repeated_ats_ids_for_same_employer_role_are_not_distinct_jobs(self):
        site = [{"company": "Example", "role": "Old Job",
                 "apply": "https://job-boards.greenhouse.io/example/jobs/1"}]
        def fake(url, body=None):
            return {"jobs": [
                {"id": 2, "title": "HR Intern",
                 "absolute_url": "https://job-boards.greenhouse.io/example/jobs/2",
                 "location": {"name": "Hyderabad"}, "content": "0-1 years experience"},
                {"id": 3, "title": "HR Intern",
                 "absolute_url": "https://job-boards.greenhouse.io/example/jobs/3",
                 "location": {"name": "Hyderabad"}, "content": "0-1 years experience"},
                {"id": 4, "title": "Graduate Engineer Trainee",
                 "absolute_url": "https://job-boards.greenhouse.io/example/jobs/4",
                 "location": {"name": "Bengaluru"}, "content": "0-2 years experience"},
            ]}
        result = a.discover(site, fetcher=fake)
        self.assertEqual(result["candidateCount"], 2)
        self.assertEqual(result["scans"][0]["duplicateInDiscovery"], 1)

    def test_lever_and_ashby(self):
        def fake(url, body=None):
            if "lever.co" in url:
                return [{"id": "u2", "text": "Software Engineering Intern",
                    "hostedUrl": "https://jobs.lever.co/testlever/u2",
                    "categories": {"location": "Pune", "commitment": "Internship"},
                    "description": "<p>New grads welcome</p>", "country": "IN"}]
            return {"jobs": [{"id": "u3", "title": "Graduate Engineer Trainee",
                "jobUrl": "https://jobs.ashbyhq.com/testashby/u3",
                "location": "Bengaluru", "descriptionHtml": "Early careers",
                "address": {"postalAddress": {"addressCountry": "IN"}}}]}
        jobs = [{"company": "Lever Employer", "role": "Old", "apply": "https://jobs.lever.co/testlever/u1"},
                {"company": "Ashby Employer", "role": "Old", "apply": "https://jobs.ashbyhq.com/testashby/u1"}]
        result = a.discover(jobs, fetcher=fake)
        self.assertEqual(result["candidateCount"], 2)
        self.assertTrue(all(x["sourceProvider"] in {"lever", "ashby"} for x in result["candidates"]))

    def test_smartrecruiters_pagination_budget_and_details(self):
        site = [{"company": "Smart Employer", "role": "Old Job",
                 "apply": "https://jobs.smartrecruiters.com/smartemployer/old"}]
        calls = []
        def fake(url, body=None):
            calls.append(url)
            if "postings?" in url:
                return {"totalFound": 200,
                    "content": [{"id": "id-"+str(i), "name": "Graduate Engineer Trainee",
                       "location": {"city": "Bengaluru", "country": "in"}}
                       for i in range(100)]}
            return {"postingUrl": "https://jobs.smartrecruiters.com/smartemployer/" + url.rsplit("/",1)[-1],
                    "jobAd": {"sections": {"jobDescription": {"text": "0-2 years"}}}}
        report = a.discover(site, fetcher=fake, max_pages=1, max_details=2)
        self.assertEqual(report["candidateCount"], 2)
        self.assertEqual(report["scans"][0]["status"], "partial")
        self.assertFalse(report["scans"][0]["complete"])
        self.assertEqual(len([x for x in calls if "postings?" in x]), 1)

    def test_workday_partial_no_expiry(self):
        site = [{"company": "Workday Employer", "role": "Old",
                 "apply": "https://company.wd3.myworkdayjobs.com/en-US/Careers/job/Bengaluru/Old_R1"}]
        def fake(url, body=None):
            if body is not None:
                return {"total": 2000, "jobPostings": [{"title": "Graduate Engineer Trainee",
                    "externalPath": "/job/Bengaluru/Graduate_R2", "locationsText": "Bengaluru"}]}
            return {"jobPostingInfo": {"title": "Graduate Engineer Trainee",
                "jobDescription": "Freshers welcome", "startDate": "2026-10-30"}}
        report = a.discover(site, fetcher=fake, max_pages=1)
        self.assertEqual(report["candidateCount"], 1)
        self.assertEqual(report["partialOrFailedBoards"], 1)
        self.assertFalse(report["expiryDecisionsAllowed"])
        self.assertTrue(report["scans"][0]["notes"])

    def test_bad_source_response_fails_closed(self):
        site = [{"company": "Broken", "apply": "https://job-boards.greenhouse.io/broken/jobs/123"}]
        report = a.discover(site, fetcher=lambda url, body=None: {"wrong": []})
        self.assertEqual(report["scans"][0]["status"], "error")
        self.assertEqual(report["candidateCount"], 0)
        self.assertFalse(report["expiryDecisionsAllowed"])


if __name__ == "__main__":
    unittest.main()
