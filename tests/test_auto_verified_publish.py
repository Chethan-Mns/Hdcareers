import sys,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from select_auto_verified_jobs import select
class AutomaticPublishing(unittest.TestCase):
 def setUp(self):
  self.now=datetime(2026,11,22,7,0,tzinfo=timezone.utc)
  url="https://jobs.ashbyhq.com/abc/12345678-1234-1234-1234-123456789123"
  self.job={"company":"Example","role":"Software Engineer Intern","loc":"Bengaluru",
   "elig":"Recent engineering graduates and college students are eligible to apply",
   "desc":"Develop and test software features with a cross-functional team, write clear documentation, review production code and work on code quality.",
   "apply":url,"sourceName":"Example ATS","resp":["Implement code"],"skills":["Python"],
   "cat":"internship","expType":"internship/apprenticeship","expYears":"Student internship","status":"unreviewed"}
  self.item={"id":"ex-1","company":"Example","apply":url,"job":self.job,
   "reviewedStatus":"unreviewed","precheckStatus":"source-active",
   "precheckReason":"Ashby public posting inventory contains the exact published job",
   "precheckCheckedAt":(self.now-timedelta(hours=1)).isoformat()}
  self.batch={"batchId":"2026-11-22-0900-ist","generatedAt":(self.now-timedelta(hours=2)).isoformat(),
              "status":"reviewing","priority":[self.item],"backup":[]}
 def run_select(self,old=None,pending=None,ledger=None):
  return select(self.batch,old or [],pending or [],ledger or {"batches":[]},now=self.now)[0]
 def test_accepts_verified_internship(self):
  selected=self.run_select()
  self.assertEqual(len(selected),1)
  self.assertEqual(selected[0][1]["expType"],"fresher")
  self.assertTrue(selected[0][1]["autoVerified"])
  self.assertNotIn("manualLiveVerifiedAt",selected[0][1])
 def test_uncertain_holds(self):
  self.item["precheckStatus"]="unsure";self.assertEqual(self.run_select(),[])
 def test_expired_decision_holds(self):
  self.item["reviewedStatus"]="expired";self.assertEqual(self.run_select(),[])
 def test_old_evidence_holds(self):
  self.item["precheckCheckedAt"]=(self.now-timedelta(days=2)).isoformat()
  self.assertEqual(self.run_select(),[])
 def test_stale_batch_holds(self):
  self.batch["batchId"]="2026-11-21-0900-ist";self.assertEqual(self.run_select(),[])
 def test_already_published_holds(self):
  self.assertEqual(self.run_select(old=[self.job]),[])
 def test_in_review_queue_holds(self):
  self.assertEqual(self.run_select(pending=[{"state":"review","job":self.job}]),[])
 def test_claimed_batch_holds(self):
  self.assertEqual(self.run_select(ledger={"batches":[{"batchId":self.batch["batchId"]}]}),[])
 def test_incorrect_employer_redirect_holds(self):
  self.item["apply"]=self.job["apply"]="https://talentbridge.cisco.com/en/job/other-company"
  self.assertEqual(self.run_select(),[])
 def test_4_years_holds(self):
  self.job["expYears"]="Minimum 4 years experience";self.assertEqual(self.run_select(),[])
 def test_missing_description_holds(self):
  self.job["desc"]="";self.assertEqual(self.run_select(),[])
 def test_one_job_per_employer(self):
  second=dict(self.item,id="ex-2",job=dict(self.job,role="Junior Software Engineer"))
  second["apply"]="https://jobs.ashbyhq.com/abc/22345678-1234-1234-1234-123456789123"
  second["job"]["apply"]=second["apply"]
  self.batch["backup"]=[second]
  self.assertEqual(len(self.run_select()),1)
if __name__=="__main__":unittest.main()
