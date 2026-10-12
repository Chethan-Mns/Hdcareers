import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from discovery_v3_source_registry import BY_NAME
from discovery_v3_probe_employers import probe, employer_links

class ProbeTests(unittest.TestCase):
    def test_scout_is_never_a_live_job(self):
        employer=BY_NAME["Capgemini"]
        html='<html><script src="https://rmkcdn.successfactors.com/test.js"></script><a href="/in-en/job-search">Search jobs</a></html>'
        r=probe(employer,fetch=lambda s:{"url":s.url,"status":200,"body":html})
        self.assertEqual(r["status"],"scouted")
        self.assertEqual(r["jobCount"],None)
        self.assertFalse(r["canPublish"])
        self.assertFalse(r["canExpire"])
        self.assertEqual(r["family"],"successfactors-like")
        self.assertEqual(len(r["sampleLinks"]),1)

    def test_external_job_board_links_are_not_collected(self):
        html='<a href="https://fake.example.com/job/fraud">Apply</a><a href="/in-en/job-search">Jobs</a>'
        result=employer_links(html,"https://jobs.capgemini.com/in-en","jobs.capgemini.com")
        self.assertEqual(len(result),1)
        self.assertIn("jobs.capgemini.com",result[0]["url"])

    def test_cross_host_redirect_requires_independent_mapping(self):
        source=BY_NAME["Accenture"]
        result=probe(source,fetch=lambda s:{"url":"https://unauthorized.example/jobs",
                   "status":200,"body":"jobs are live"})
        self.assertEqual(result["status"],"needs_manual_mapping")
        self.assertFalse(result["canPublish"])

    def test_blocked_portal_never_implies_expiry(self):
        result=probe(BY_NAME["Infosys"],fetch=lambda s:{"url":s.url,"status":403,
                     "body":"Access denied"})
        self.assertEqual(result["status"],"unconfirmed")
        self.assertEqual(result["jobCount"],None)
        self.assertFalse(result["canExpire"])

    def test_cannot_skip_unverified_registry_stage(self):
        result=probe(BY_NAME["Deloitte South Asia"])
        self.assertEqual(result["status"],"unconfirmed")
        self.assertEqual(result["reason"],"Not a new-employer probe")

if __name__=="__main__":
    unittest.main()
