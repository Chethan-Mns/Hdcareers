"""Production post-review characterization tests. Read only; no mutations."""
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class OwnerReview39(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit=json.loads((ROOT/"data/owner-manual-expiry-review-20261015.json").read_text())
        cls.jobs={j["id"]:j for j in json.loads((ROOT/"data/jobs.json").read_text())}
        cls.scan=json.loads((ROOT/"data/availability-status.json").read_text())
        cls.report={x["id"]:x for x in cls.scan["items"]}
        cls.sitemap=(ROOT/"sitemap.xml").read_text()
        cls.home=(ROOT/"index.html").read_text()
    def test_all_39_decisions_and_urls_are_preserved(self):
        changes=self.audit["changes"]
        self.assertEqual(len(changes),39)
        self.assertEqual(len({x["id"] for x in changes}),39)
        self.assertEqual(sum(x["ownerVerdict"]=="Expired" for x in changes),9)
        self.assertEqual(sum(x["ownerVerdict"]=="Active" for x in changes),30)
        for entry in changes:
            with self.subTest(id=entry["id"]):
                job=self.jobs[entry["id"]]
                verdict=entry["ownerVerdict"].lower()
                self.assertEqual(job["status"],verdict)
                self.assertEqual(job["apply"],entry["officialUrl"])
                self.assertEqual(job["ownerReviewEvidence"]["officialUrl"],entry["officialUrl"])
                self.assertEqual(job["ownerReviewEvidence"]["status"],verdict)
                if verdict=="expired":
                    self.assertEqual(job["manualClosedVerifiedUrl"],entry["officialUrl"])
                    self.assertTrue(job["manualClosedVerifiedAt"])
                    self.assertNotIn("manualLiveVerifiedAt",job)
                else:
                    self.assertEqual(job["manualLiveVerifiedUrl"],entry["officialUrl"])
                    self.assertTrue(job["manualLiveVerifiedAt"])
                    self.assertNotIn("manualClosedVerifiedAt",job)
                self.assertEqual(self.report[entry["id"]]["state"],verdict)
                self.assertEqual(self.report[entry["id"]]["manualReviewedUrl"],entry["officialUrl"])
    def test_all_nine_expired_pages_closed_and_off_sitemap(self):
        for entry in self.audit["changes"]:
            if entry["ownerVerdict"]!="Expired":continue
            job=self.jobs[entry["id"]]
            with self.subTest(id=entry["id"]):
                html=(ROOT/job["page"]).read_text()
                self.assertIn('name="robots" content="noindex,follow"',html)
                self.assertIn("Application Closed",html)
                self.assertNotIn('"@type": "JobPosting"',html)
                self.assertNotIn("https://hdcareers.in/"+job["page"],self.sitemap)
    def test_active_jobs_still_in_sitemap(self):
        for entry in self.audit["changes"]:
            if entry["ownerVerdict"]!="Active":continue
            job=self.jobs[entry["id"]]
            with self.subTest(id=entry["id"]):
                self.assertIn("https://hdcareers.in/"+job["page"],self.sitemap)
    def test_database_and_snapshot_counts(self):
        self.assertEqual(len(self.jobs),131)
        self.assertEqual(sum(x["status"]=="active" for x in self.jobs.values()),100)
        self.assertEqual(sum(x["status"]=="expired" for x in self.jobs.values()),31)
        self.assertEqual(self.scan["checked"],109)
        self.assertEqual(self.scan["active"],100)
        self.assertEqual(self.scan["expired"],9)
        self.assertEqual(self.scan["review"],0)
        self.assertEqual(self.audit["recordedAt"],self.scan["lastManualReviewAt"])
if __name__=="__main__":unittest.main()
