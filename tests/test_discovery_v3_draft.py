import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from discovery_v3_draft import extract_facts

URL = "https://careers.ey.com/ey/job/Mumbai-Analyst/123456789/"
TITLE = "Associate Analyst"
NOW = datetime(2026,10,12,tzinfo=timezone.utc)

def document(**changes):
    post = {
        "@type": "JobPosting",
        "url": URL,
        "title": TITLE,
        "hiringOrganization": {"name": "EY"},
        "description": "<p>Support tax reporting and client deliverables.</p>",
        "qualifications": "B.Com degree; 0–1 years of experience",
        "responsibilities": "Prepare tax reporting inputs accurately",
        "jobLocation": {"address":{"addressLocality":"Mumbai","addressCountry":"IN"}},
        "datePosted":"2026-10-08",
        "validThrough":"2026-10-30"
    }
    post.update(changes)
    return '<html><script type="application/ld+json">'+json.dumps(post)+'</script></html>'


class DraftTests(unittest.TestCase):
    def test_exact_official_structured_job_creates_content_ready_draft(self):
        result=extract_facts(document(),URL,"EY",TITLE,NOW)
        self.assertEqual(result["status"],"content_ready")
        self.assertEqual(result["missing"],[])
        self.assertEqual(result["facts"]["elig"],"B.Com degree; 0–1 years of experience")
        self.assertEqual(result["facts"]["loc"],"Mumbai, IN")
        self.assertEqual(result["facts"]["apply"],URL)

    def test_missing_qualifications_do_not_get_invented(self):
        result=extract_facts(document(qualifications=None),URL,"EY",TITLE,NOW)
        self.assertEqual(result["status"],"incomplete")
        self.assertIn("elig",result["missing"])
        self.assertEqual(result["facts"]["elig"],"")

    def test_mismatched_title_company_or_url_refused(self):
        for changes in (
            {"title":"Finance Manager"},
            {"hiringOrganization":{"name":"Unknown Consultancy"}},
            {"url":"https://careers.ey.com/ey/job/SomeOther/123456789/"},
            {"url":"https://fraud.example/ey/job/Mumbai-Analyst/123456789/"},
            {"jobLocation":{"address":{"addressCountry":"US"}}},
        ):
            self.assertEqual(extract_facts(document(**changes),URL,"EY",TITLE,NOW)["status"],"unconfirmed")

    def test_past_deadline_is_not_published(self):
        result=extract_facts(document(validThrough="2026-10-01"),URL,"EY",TITLE,NOW)
        self.assertEqual(result["status"],"unconfirmed")
        self.assertIn("deadline",result["reason"])

    def test_invalid_or_missing_json_is_unconfirmed(self):
        self.assertEqual(extract_facts("<html><script type='application/ld+json'>{broken}</script></html>",
                                       URL,"EY",TITLE,NOW)["status"],"unconfirmed")

if __name__=="__main__":
    unittest.main()
