import sys
from datetime import datetime,timedelta,timezone
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from reel_factory import choose_job,storyboard

class ReelFactoryTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,9,12,0,tzinfo=timezone.utc)
        self.job={"id":12,"company":"Deloitte","role":"Associate Analyst",
            "roleTag":"Associate Analyst","loc":"Bengaluru","field":"it","expType":"fresher",
            "status":"active","page":"jobs/deloitte.html","apply":"https://example.org/12"}
        self.scan={"items":[{"id":12,"state":"active","checkedAt":(self.now-timedelta(hours=1)).isoformat()}]}
    def test_verified_job(self):
        self.assertEqual(choose_job([self.job],self.scan,set(),now=self.now)["id"],12)
    def test_unverified_job(self):
        self.scan["items"][0]["state"]="review"
        self.assertIsNone(choose_job([self.job],self.scan,set(),now=self.now))
    def test_expired_job(self):
        self.job["status"]="expired"
        self.assertIsNone(choose_job([self.job],self.scan,set(),now=self.now))
    def test_duplicate(self):
        self.assertIsNone(choose_job([self.job],self.scan,{"12"},now=self.now))
    def test_stale_evidence(self):
        self.scan["items"][0]["checkedAt"]=(self.now-timedelta(days=2)).isoformat()
        self.assertIsNone(choose_job([self.job],self.scan,set(),now=self.now))
    def test_caption(self):
        p=storyboard(self.job)
        self.assertIn("APPLY",p["script"])
        self.assertIn("https://hdcareers.in/jobs/deloitte.html",p["caption"])
        self.assertLessEqual(len(p["script"].split()),40)

if __name__=="__main__":unittest.main()
