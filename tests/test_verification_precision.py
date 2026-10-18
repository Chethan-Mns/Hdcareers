import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from check_job_availability import (official_inventory_probe, has_high_confidence_live,
                                    expiry_decision, classify, normalize_role_heading,
                                    oracle_rendered_evidence, successfactors_exact_page,
                                    is_oracle_candidate_url)
from preflight_live_shortlist import preflight

T=datetime(2026,10,18,3,30,tzinfo=timezone.utc)
WORKDAY={"id":1,"company":"Deutsche Bank","role":"Apprentice Hiring for 2026-2027",
         "apply":"https://db.wd3.myworkdayjobs.com/en-US/DBWebsite/job/Mumbai/Apprentice---Non-Technology_R0357981"}
HTML={"id":2,"company":"Example","role":"Software Engineer",
      "apply":"https://careers.example.com/jobs/123"}

class PrecisionTests(unittest.TestCase):
 def test_oracle_rendered_exact_requisition_positive(self):
  oracle={"company":"JPMorganChase","role":"Disclosure of Interest Analyst",
    "jobId":"210794554","apply":"https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1002/job/210794554"}
  text="Disclosure of Interest Analyst Job Identification 210794554 Job Category CCOR Foundation"
  state,reason=oracle_rendered_evidence(oracle,oracle["apply"],oracle["role"],text,True)
  self.assertEqual(state,"active")
  self.assertTrue(has_high_confidence_live(oracle,{"state":state,"reason":reason}))
  for target,heading,body,enabled in [
    (oracle["apply"],oracle["role"],text,False),
    (oracle["apply"],oracle["role"],"Job Identification 210794999 Disclosure of Interest Analyst",True),
    (oracle["apply"],"Other Job",text,True),
    (oracle["apply"].replace("/job/210794554","/jobs"),oracle["role"],text,True),
    (oracle["apply"],oracle["role"],text+" This job is closed",True),
  ]:
   with self.subTest(heading=heading,target=target):
    self.assertEqual(oracle_rendered_evidence(oracle,target,heading,body,enabled)[0],"review")
  self.assertTrue(is_oracle_candidate_url(oracle["apply"]))
  self.assertFalse(is_oracle_candidate_url("http://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1002/job/210794554"))
  # Browser-like HTML alone does not qualify Oracle; must use exact rendered proof.
  self.assertFalse(has_high_confidence_live(oracle,{"state":"active","reason":"Browser-compatible official-page render is active (Exact role and application call-to-action found on official URL)"}))

 def test_sap_successfactors_exact_requisition_and_real_apply_link(self):
  sap={"company":"SAP","role":"Solution Advisor Associate - SAP Academy for Customer Success - INDIA",
      "jobId":"458688","apply":"https://jobs.sap.com/job/New-Delhi-Solution-Advisor-Associate-SAP-Academy-for-Customer-Success-INDIA-110017/1426371233/"}
  page='<h1>'+sap["role"]+'</h1><p>Requisition ID: 458688</p><a href="'+sap["apply"]+'apply">Apply now »</a>'
  status,why=successfactors_exact_page(sap,page,sap["apply"])
  self.assertEqual(status,"active")
  self.assertTrue(has_high_confidence_live(sap,{"state":status,"reason":why}))
  for content,final in [
    (page.replace("458688","999999"),sap["apply"]),
    (page.replace('<a href="'+sap["apply"]+'apply">Apply now »</a>',"<span>Apply now</span>"),sap["apply"]),
    (page,sap["apply"].replace("/1426371233/","/other/")),
    ("<h1>Other role</h1><p>Requisition ID: 458688</p><a href='/apply'>Apply now</a>",sap["apply"]),
  ]:
   self.assertEqual(successfactors_exact_page(sap,content,final)[0],"review")
 def test_employer_hosted_sap_successfactors_trainee_page(self):
  job={"company":"SIA Engineering Company",
       "role":"Aircraft Maintenance License Trainee (AMLT)",
       "jobId":"767",
       "apply":"https://careers.singaporeair.com/siaec/job/Aircraft-Maintenance-License-Trainee-%28AMLT%29/19970444/"}
  html="<h1>Aircraft Maintenance License Trainee (AMLT)</h1><p>Requisition ID: 767</p><a href='/siaec/job/Aircraft-Maintenance-License-Trainee-%28AMLT%29/19970444/apply'>Apply now</a>"
  status,reason=successfactors_exact_page(job,html,job["apply"])
  self.assertEqual(status,"active")
  self.assertTrue(has_high_confidence_live(job,{"state":status,"reason":reason}))
  self.assertEqual(successfactors_exact_page(job,html.replace("Requisition ID: 767","Requisition ID: 999"),job["apply"])[0],"review")
  self.assertEqual(successfactors_exact_page(job,html.replace("Apply now","Learn more"),job["apply"])[0],"review")
 def test_seventh_source_is_official_qa_only_and_preserves_first_six(self):
  base=json.loads((ROOT/"data/testing/ats-platform-six-20261018.json").read_text())
  seven=json.loads((ROOT/"data/testing/ats-platform-seven-20261018.json").read_text())
  self.assertEqual(len(base["jobs"]),6)
  self.assertEqual(len(seven["jobs"]),7)
  self.assertEqual(base["jobs"],seven["jobs"][:6])
  self.assertEqual(seven["jobs"][6]["reqId"],"767")
  self.assertEqual(seven["jobs"][6]["brandDomain"],"siaec.com.sg")
  self.assertEqual(seven["mode"],"qa-isolated-no-production-publishing")
 def test_exact_workday_native_active(self):
  payload={"jobPostingInfo":{"jobReqId":"R0357981","title":"Apprentice Hiring for 2026-2027","canApply":True}}
  with patch("check_job_availability.fetch_json",return_value=payload) as fetch:
   state,reason=official_inventory_probe(WORKDAY)
  self.assertEqual(state,"active")
  self.assertTrue(has_high_confidence_live(WORKDAY,{"state":state,"reason":reason}))
  self.assertIn("/wday/cxs/db/DBWebsite/job/Mumbai/Apprentice---Non-Technology_R0357981",fetch.call_args.args[0])
 def test_workday_blank_shell_or_missing_explicit_apply_is_not_live(self):
  for info in ({},{"jobReqId":"R0357981","title":"Apprentice"},{"jobReqId":"WRONG","title":"Apprentice","canApply":True}):
   with self.subTest(info=info),patch("check_job_availability.fetch_json",return_value={"jobPostingInfo":info}):
    self.assertEqual(official_inventory_probe(WORKDAY)[0],"review")
  self.assertFalse(has_high_confidence_live(WORKDAY,{"state":"active","reason":"Browser-compatible official-page render is active (Exact role and application call-to-action found on official URL)"}))
 def test_workday_explicit_close(self):
  with patch("check_job_availability.fetch_json",return_value={"jobPostingInfo":{"jobReqId":"R0357981","title":"Apprentice","canApply":False}}):
   r=official_inventory_probe(WORKDAY)
  self.assertEqual(r[0],"expired")
  self.assertEqual(expiry_decision(WORKDAY,{"state":r[0],"reason":r[1]},now=T)["state"],"expired")
 def test_first_soft_close_is_held_until_independent_scan(self):
  old={"state":"expired","reason":"Job not found","url":HTML["apply"]}
  first=expiry_decision(HTML,old,now=T)
  self.assertEqual(first["state"],"review")
  self.assertEqual(first["observedState"],"expired")
  second=expiry_decision(HTML,old,previous={"url":HTML["apply"],"state":"review","observedState":"expired",
    "checkedAt":(T-timedelta(hours=12)).isoformat()},now=T)
  self.assertEqual(second["state"],"expired")
  self.assertEqual(second["expiryEvidence"],"independent-consecutive-scans")
 def test_repeating_scan_too_soon_or_different_url_does_not_expire(self):
  for mismatch in ({"checkedAt":(T-timedelta(minutes=10)).isoformat(),"url":HTML["apply"]},
                   {"checkedAt":(T-timedelta(hours=12)).isoformat(),"url":"https://elsewhere.example.com"}):
   with self.subTest(prior=mismatch):
    previous={**mismatch,"observedState":"expired","state":"review"}
    self.assertEqual(expiry_decision(HTML,{"state":"expired","reason":"This job is closed"},previous=previous,now=T)["state"],"review")
 def test_lever_typography_only_normalizes_visible_exact_job_title(self):
  job={"id":3,"company":"AHEAD","role":"MS – EUS Apprentice/Intern (6 months)",
       "apply":"https://jobs.lever.co/thinkahead/7950d5ca-0cf8-4fa5-a2fc-6210c711411f"}
  url=job["apply"]
  html="<h1>MS - EUS Apprentice/Intern (6 months)</h1><a href='"+url+"/apply'>Apply for this job</a>"
  self.assertEqual(normalize_role_heading("MS – EUS Apprentice/Intern (6 months)"),
                   normalize_role_heading("MS - EUS Apprentice/Intern (6 months)"))
  result=classify(job,html,url)
  self.assertEqual(result[0],"active")
  self.assertTrue(has_high_confidence_live(job,{"state":result[0],
       "reason":"Browser-compatible official-page render is active ("+result[1]+")"}))
  self.assertEqual(classify(job,"<h1>MS - NOC Apprentice/Intern (6 months)</h1><p>Apply for this job</p>",url)[0],"review")
  self.assertEqual(classify(job,"<h1>MS - EUS Apprentice/Intern (6 months)</h1>",url)[0],"review")
  self.assertEqual(classify(job,html,"https://jobs.lever.co/thinkahead/other-posting")[0],"review")
 def test_owner_ground_truth_is_recorded_without_publishing(self):
  j=json.loads((ROOT/"data/testing/ats-platform-six-owner-ground-truth-20261018.json").read_text())
  self.assertFalse(j["productionPublishAuthorized"])
  self.assertEqual(j["batchId"],"ats-six-sources-2026-10-18")
  self.assertEqual(len(j["jobs"]),6)
  self.assertEqual(sum(x["manualVerdict"]=="live" for x in j["jobs"]),4)
  self.assertEqual(sum(x["manualVerdict"]=="expired" for x in j["jobs"]),2)
  tp=sum(x["manualVerdict"]=="live" and x["checkerVerifiedLive"] for x in j["jobs"])
  fp=sum(x["manualVerdict"]!="live" and x["checkerVerifiedLive"] for x in j["jobs"])
  self.assertEqual((tp,fp),(2,0))
  self.assertEqual(j["eligibilityNote"]["id"],"oracle-jpmc")
 def test_exact_html_apply_is_eligible_but_old_manual_override_is_not(self):
  strong={"state":"active","reason":"Browser-compatible official-page render is active (Exact role and application call-to-action found on official URL)"}
  self.assertTrue(has_high_confidence_live(HTML,strong))
  self.assertFalse(has_high_confidence_live(HTML,{"state":"active","reason":"Recent exact-job manual confirmation overrides inconclusive automated result"}))
 def test_morning_list_keeps_only_strong_live_and_preserves_held_rows(self):
  items=[
   {"id":"a","company":"Example","apply":HTML["apply"],"job":HTML,"reviewedStatus":"unreviewed"},
   {"id":"b","company":"Deutsche Bank","apply":WORKDAY["apply"],"job":WORKDAY,"reviewedStatus":"unreviewed"},
  ]
  def checker(job,now=None):
   if job["id"]==2:return {"state":"active","reason":"Browser-compatible official-page render is active (Exact role and application call-to-action found on official URL)"}
   return {"state":"review","reason":"Workday exact requisition without active application evidence"}
  batch={"status":"reviewing","batchId":"test","priority":items,"backup":[]}
  out,report=preflight(batch,checker=checker,now=T,workers=2)
  self.assertEqual(len(out["priority"]),1)
  self.assertEqual(len(out["backup"]),0)
  self.assertEqual(len(out["verificationHold"]),1)
  self.assertEqual(report["heldForReview"],1)
  self.assertEqual(batch["priority"],items)
  self.assertEqual(out["priority"][0]["liveSourceEvidence"]["decision"],"verified_live")
 def test_never_edit_manual_review_or_published_batch(self):
  item={"id":"a","reviewedStatus":"expired","reviewedAt":T.isoformat()}
  original={"status":"reviewing","priority":[item],"backup":[]}
  out,report=preflight(original,checker=lambda *_:self.fail("network not expected"))
  self.assertTrue(report["skipped"])
  self.assertEqual(out,original)
 def test_no_strong_candidates_means_zero_priority_not_false_lives(self):
  row={"id":"x","company":"Example","apply":HTML["apply"],"job":HTML}
  out,rep=preflight({"status":"reviewing","priority":[row],"backup":[]},
   checker=lambda job,now=None:{"state":"review","reason":"inaccessible"},now=T)
  self.assertEqual(out["priority"],[])
  self.assertEqual(rep["heldForReview"],1)

class BrandingTests(unittest.TestCase):
 def test_generic_workday_host_not_used_as_brand_source(self):
  import generate
  employer={"company":"Unmapped Company","domain":"tenant.wd3.myworkdayjobs.com",
            "apply":"https://tenant.wd3.myworkdayjobs.com/jobs/123"}
  self.assertEqual(generate._company_logo_domain(employer),"")
  self.assertEqual(generate.logo_sources(employer["company"],employer["domain"]),("",""))
  self.assertFalse(any("workday" in x for x in generate.logo_candidates(employer)))
 def test_known_workday_tenant_uses_actual_employer(self):
  import generate
  j=dict(WORKDAY,domain="db.wd3.myworkdayjobs.com")
  self.assertEqual(generate._company_logo_domain(j),"db.com")
  self.assertTrue(any("db.com" in x for x in generate.logo_candidates(j)))
  self.assertFalse(any("myworkdayjobs.com" in x for x in generate.logo_candidates(j)))
 def test_careers_favicon_source_must_match_employer_domain(self):
  from resolve_company_logos import candidate_urls
  def fetched(url,limit):
   return (b'<html><link rel="icon" href="https://careers.db.com/favicon.svg"></html>',
           "text/html",url)
  with patch("resolve_company_logos.fetch",side_effect=fetched):
   c=candidate_urls("db.com",careers_url="https://careers.db.com/")
  self.assertTrue(any("careers.db.com/favicon.svg" in row[1] for row in c))
  self.assertFalse(any("myworkdayjobs.com" in row[1] for row in c))

if __name__=="__main__":
 unittest.main()
