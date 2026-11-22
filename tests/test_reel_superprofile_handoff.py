import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from reel_superprofile_handoff import draft


class SuperProfileHandoffTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {
            "jobId": 10,
            "company": "Deloitte",
            "role": "Associate Analyst",
            "page": "jobs/deloitte-associate-analyst.html",
            "jobUrl": "https://hdcareers.in/jobs/deloitte-associate-analyst.html",
            "caption": "Deloitte is hiring freshers. Comment APPLY for the job link.",
        }

    def test_exact_job_specific_link_and_keyword(self):
        d = draft(self.manifest)
        self.assertEqual(d["jobUrl"], d["buttonUrl"])
        self.assertEqual(d["keyword"], "APPLY")
        self.assertEqual(d["postScope"], "specific_reel")
        self.assertEqual(d["state"], "draft_not_connected")
        self.assertFalse(d["automatedMessageEnabled"])
        self.assertFalse(d["followGate"])
        self.assertIn("official application link", d["openingMessage"])

    def test_reject_external_or_mismatched_urls(self):
        for bad in (
            "https://evil.example/jobs/deloitte-associate-analyst.html",
            "http://hdcareers.in/jobs/deloitte-associate-analyst.html",
            "https://hdcareers.in/jobs/not-the-same.html",
            "https://hdcareers.in/jobs/deloitte-associate-analyst.html?redirect=other",
            "https://hdcareers.in/jobs/../../api/admin",
        ):
            with self.subTest(url=bad):
                with self.assertRaises(ValueError):
                    draft(dict(self.manifest, jobUrl=bad))

    def test_requires_matching_caption_and_job_identity(self):
        with self.assertRaises(ValueError):
            draft(dict(self.manifest, caption="No keyword here"))
        with self.assertRaises(ValueError):
            draft(dict(self.manifest, jobId=None))
        with self.assertRaises(ValueError):
            draft(dict(self.manifest, page="../secrets"))


if __name__ == "__main__":
    unittest.main()
