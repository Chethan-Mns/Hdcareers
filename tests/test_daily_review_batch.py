import unittest
import json
import tempfile
from pathlib import Path
import importlib.util

SRC=Path(__file__).resolve().parents[1]/"scripts"/"validate_daily_review_batch.py"
spec=importlib.util.spec_from_file_location("review_schema",SRC)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def item(i,company=None,full=False):
    company=company or f"VerifiedCompany{i}"
    job={"company":company,"role":f"Official role {i}","loc":"Bengaluru",
         "apply":f"https://example.com/careers/req-{i}","status":"review"}
    if full:
        job.update(status="active",elig="Verified degree",desc="Verified employer information",
                   resp=["Actual responsibility from listing"],sourceName="Official Careers")
    return {"id":f"{company}-REQ-{i}","company":company,"role":job["role"],
            "apply":job["apply"],"reviewedStatus":"unreviewed",
            "verificationReason":"Official exact requisition URL visited; source detail recorded",
            "verificationVerdict":"unconfirmed","job":job}

def batch(n=10,backups=10):
    return {"batchId":"2026-10-11-0900-ist","generatedAt":"2026-10-11T03:30:00Z",
            "status":"reviewing","updatedAt":"2026-10-11T03:33:00Z",
            "priority":[item(i,full=True) for i in range(n)],
            "backup":[item(i+100) for i in range(backups)]}

class TestDailyReviewContract(unittest.TestCase):
    def test_empty_waiting_state(self):
        self.assertEqual(mod.check({"batchId":"","generatedAt":None,"status":"waiting","priority":[],"backup":[]})["state"],"waiting")
    def test_unreviewed_batch_is_persistable(self):
        data=mod.check(batch())
        self.assertEqual((data["priority"],data["backup"],data["complete"],data["unreviewed"]),(10,10,10,20))
    def test_less_than_ten_real_jobs_allowed_for_review(self):
        self.assertEqual(mod.check(batch(6,5))["priority"],6)
    def test_invalid_source_url_rejected(self):
        p=batch();p["priority"][0]["job"]["apply"]="http://evil.example"
        with self.assertRaises(ValueError):mod.check(p)
    def test_duplicate_job_detected(self):
        p=batch();p["backup"][0]["job"]["apply"]=p["priority"][0]["job"]["apply"]
        with self.assertRaises(ValueError):mod.check(p)
    def test_verified_evidence_is_required(self):
        p=batch();p["priority"][0].pop("verificationReason")
        with self.assertRaises(ValueError):mod.check(p)
    def test_empty_job_details_remain_reviewable_but_cannot_submit(self):
        p=batch();p["priority"][0]["job"]={"company":"Comp","role":"Grad","apply":"https://example.com/careers/new","status":"review"}
        self.assertEqual(mod.check(p)["complete"],9)
        p["status"]="submitted"
        for j in p["priority"]:j.update(reviewedStatus="live",reviewedAt="2026-10-11T09:00:00Z")
        p["publication"]={"candidateIds":[p["priority"][0]["id"]]}
        with self.assertRaises(ValueError):mod.check(p)
    def test_cannot_fake_owner_approval(self):
        p=batch();p["status"]="submitted"
        with self.assertRaises(ValueError):mod.check(p)
    def test_submitted_jobs_need_ten_live_complete(self):
        p=batch();p["status"]="submitted"
        for j in p["priority"]:j.update(reviewedStatus="live",reviewedAt="2026-10-11T09:00:00Z")
        p["publication"]={"candidateIds":[p["priority"][0]["id"]]}
        self.assertEqual(mod.check(p)["state"],"submitted")
    def test_strict_discovery_rejects_duplicate_employers(self):
        p=batch();p["backup"][0]["company"]=p["priority"][0]["company"];p["backup"][0]["job"]["company"]=p["priority"][0]["company"]
        with self.assertRaisesRegex(ValueError,"Repeated employer"):mod.check(p,strict_discovery=True)
    def test_strict_discovery_requires_all_twenty(self):
        p=batch(10,8)
        for x in p["backup"]:x["job"].update(status="active",elig="Degree",desc="Source description",resp=["Verified task"],sourceName="Official Careers")
        with self.assertRaisesRegex(ValueError,"10 priority"):mod.check(p,strict_discovery=True)
    def test_strict_discovery_prioritizes_fresher_it(self):
        p=batch()
        for x in p["backup"]:x["job"].update(status="active",elig="Degree",desc="Source description",resp=["Verified task"],sourceName="Official Careers")
        for i,c in enumerate(p["priority"]+p["backup"]):c["job"]["expType"]="fresher" if i>=10 else "experienced";c["job"]["cat"]="it"
        with self.assertRaisesRegex(ValueError,"unclassified or non-fresher"):mod.check(p,strict_discovery=True)
    def test_strict_discovery_does_not_count_it_intern_as_full_time_technical(self):
        p=batch()
        for x in p["backup"]:
            x["job"].update(status="active",elig="Degree",desc="Verified role",resp=["Verified task"],sourceName="Official Careers")
        for i,c in enumerate(p["priority"]+p["backup"]):
            c["job"]["cat"]="it"
            c["job"]["expType"]="fresher"
            c["job"]["role"]="Software Engineer Intern" if i in (0,10) else "Software Engineer"
        with self.assertRaisesRegex(ValueError,"6 fresher technical"):mod.check(p,strict_discovery=True)

    def test_invalid_json_document(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"batch.json";path.write_text(json.dumps(batch(3,2)))
            self.assertEqual(mod.check(json.loads(path.read_text()))["backup"],2)

if __name__=="__main__":
    unittest.main()
