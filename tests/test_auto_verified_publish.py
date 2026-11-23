import sys,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from select_auto_verified_jobs import select, publication_bucket, category_counts, category_shortfalls, CATEGORY_TARGETS
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
  self.assertEqual(selected[0][1]["cat"],"internship")
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
 def test_credible_short_description_with_full_structured_fields_passes(self):
  # The official-source content preflight already verifies eligibility,
  # responsibilities and skill lists; 70-99 characters is acceptable.
  self.job["desc"]="Write software, test changes, support colleagues and document fixes quickly."
  self.assertGreaterEqual(len(self.job["desc"]),70)
  self.assertLess(len(self.job["desc"]),100)
  self.assertEqual(len(self.run_select()),1)
 def test_insufficient_brief_description_holds(self):
  self.job["desc"]="Brief opening."
  self.assertEqual(self.run_select(),[])

 def test_one_job_per_employer(self):
  second=dict(self.item,id="ex-2",job=dict(self.job,role="Junior Software Engineer"))
  second["apply"]="https://jobs.ashbyhq.com/abc/22345678-1234-1234-1234-123456789123"
  second["job"]["apply"]=second["apply"]
  self.batch["backup"]=[second]
  self.assertEqual(len(self.run_select()),1)

class StrictQuotaSelection(unittest.TestCase):
 """Final automated publishing must apply the same 6/2/2 mix as discovery."""
 def setUp(self):
  self.now=datetime(2026,11,23,6,0,tzinfo=timezone.utc)
  self.batch={"batchId":"2026-11-23-0900-ist",
              "generatedAt":(self.now-timedelta(hours=2)).isoformat(),
              "status":"reviewing","priority":[],"backup":[]}
 def row(self,num,category="it",exp_type="fresher",field=None,role=None):
  if field is None:field="nonit" if category=="nonit" else "it"
  role=role or ("Graduate Software Engineer" if category not in ("nonit","internship","apprenticeship")
                else ("Graduate Operations Associate" if category=="nonit" else "Software Intern"))
  url=f"https://jobs.ashbyhq.com/qualitytest/{num:08d}-aaaa-bbbb-cccc-000000000000"
  job={"company":f"Company {num}","role":role,"loc":"Hyderabad",
       "elig":"Graduates and freshers meeting official eligibility are welcome",
       "desc":"Work with the relevant employer team, complete scoped tasks, collaborate across departments, deliver quality work and document assigned projects.",
       "apply":url,"sourceName":"Official employer ATS","resp":["Deliver assigned work"],
       "skills":["Communication"],"cat":category,"field":field,"expType":exp_type,
       "expYears":"0 to 1 years","status":"unreviewed"}
  return {"id":f"verified-{num}","company":job["company"],"apply":url,"job":job,
          "reviewedStatus":"unreviewed","precheckStatus":"source-active",
          "precheckReason":"Exact role and application call-to-action found on official URL",
          "precheckCheckedAt":(self.now-timedelta(minutes=45)).isoformat()}
 def choose(self,limit=10):
  return select(self.batch,[],[],{"batches":[]},now=self.now,limit=limit)[0]
 def counts(self,chosen):
  return category_counts(chosen)

 def test_priority_plus_backup_fill_exact_quota_without_publishing_surplus_it(self):
  # Priority contains the obsolete 8/1/1 mix, but selection must be 6/2/2.
  self.batch["priority"]=[self.row(i) for i in range(1,9)]+[
     self.row(9,"nonit"),self.row(10,"internship","internship/apprenticeship")]
  self.batch["backup"]=[self.row(11),self.row(12,"nonit"),
                         self.row(13,"apprenticeship","internship/apprenticeship")]
  chosen=self.choose()
  self.assertEqual(len(chosen),10)
  self.assertEqual(self.counts(chosen),CATEGORY_TARGETS)
  ids={id for id,_ in chosen}
  self.assertTrue({"verified-12","verified-13"}.issubset(ids))
  self.assertFalse({"verified-7","verified-8","verified-11"}.intersection(ids))
  self.assertEqual(len({job["company"] for _,job in chosen}),10)
  self.assertEqual(category_shortfalls(self.counts(chosen)),
                   {"technicalFullTime":0,"nonTechFullTime":0,"internshipOrApprenticeship":0})

 def test_no_filler_if_training_or_non_it_short(self):
  self.batch["priority"]=[self.row(i) for i in range(1,10)]+[self.row(10,"nonit")]
  self.batch["backup"]=[self.row(11),self.row(12),self.row(13,"nonit")]
  chosen=self.choose()
  self.assertEqual(len(chosen),8)
  self.assertEqual(self.counts(chosen),
                   {"technicalFullTime":6,"nonTechFullTime":2,"internshipOrApprenticeship":0})
  self.assertEqual(category_shortfalls(self.counts(chosen))["internshipOrApprenticeship"],2)

 def test_skip_unsure_and_expired_training_instead_of_counting_it_filler(self):
  self.batch["priority"]=[self.row(i) for i in range(1,7)]+[
     self.row(7,"nonit"),self.row(8,"nonit"),
     self.row(9,"internship","internship/apprenticeship"),
     self.row(10,"apprenticeship","internship/apprenticeship")]
  self.batch["priority"][8]["precheckStatus"]="unsure"
  self.batch["priority"][9]["reviewedStatus"]="expired"
  self.batch["backup"]=[self.row(11),self.row(12),
                         self.row(13,"internship","internship/apprenticeship")]
  chosen=self.choose()
  self.assertEqual(len(chosen),9)
  self.assertEqual(self.counts(chosen),
                   {"technicalFullTime":6,"nonTechFullTime":2,"internshipOrApprenticeship":1})
  self.assertEqual([job["company"] for _,job in chosen if publication_bucket(job)=="internshipOrApprenticeship"],
                   ["Company 13"])

 def test_deny_training_wrongly_tagged_it_but_accept_fresher_typed_training(self):
  rows=[self.row(1,"it","internship/apprenticeship",role="Software Intern"),
        self.row(2,"internship","fresher",role="Software Intern"),
        self.row(3,"it","fresher",role="Software Intern"),
        self.row(4,"it","fresher",field="nonit"),
        self.row(5,"nonit","fresher",field="it"),
        self.row(6,"campus","fresher",field="it"),
        self.row(7,"apprenticeship","internship/apprenticeship")]
  self.batch["priority"]=rows
  chosen=self.choose()
  self.assertEqual([id for id,_ in chosen],["verified-2","verified-6","verified-7"])
  self.assertEqual(self.counts(chosen)["internshipOrApprenticeship"],2)
  self.assertEqual(chosen[-1][1]["expType"],"fresher")
  self.assertEqual(chosen[-1][1]["cat"],"apprenticeship")

 def test_no_double_counting_same_employer_across_categories(self):
  first=self.row(1,"it")
  duplicate=self.row(2,"nonit")
  duplicate["job"]["company"]=first["job"]["company"]
  self.batch["priority"]=[first]
  self.batch["backup"]=[duplicate]
  chosen=self.choose()
  self.assertEqual(len(chosen),1)
  self.assertEqual(self.counts(chosen),
                   {"technicalFullTime":1,"nonTechFullTime":0,"internshipOrApprenticeship":0})

 def test_limit_never_overruns_bucket_caps(self):
  self.batch["priority"]=[self.row(i) for i in range(1,11)]
  self.batch["backup"]=[self.row(11,"nonit"),self.row(12,"nonit"),
                         self.row(13,"internship","internship/apprenticeship"),
                         self.row(14,"apprenticeship","internship/apprenticeship")]
  chosen=self.choose(limit=50)
  self.assertEqual(len(chosen),10)
  self.assertEqual(self.counts(chosen),CATEGORY_TARGETS)

if __name__=="__main__":unittest.main()
