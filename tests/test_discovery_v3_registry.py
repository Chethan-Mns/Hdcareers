import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from discovery_v3_source_registry import EMPLOYERS, BY_NAME, Employer, fingerprint

class RegistryTests(unittest.TestCase):
    def test_all_priority_employers_registered_no_duplicates(self):
        self.assertEqual(len(EMPLOYERS),11)
        self.assertEqual(len({e.name for e in EMPLOYERS}),len(EMPLOYERS))
        self.assertEqual(BY_NAME["HCLTech"].stage,"shadow")
        self.assertEqual(BY_NAME["KPMG India"].family,"multiple-portals")

    def test_no_unverified_employer_is_allowed_to_publish(self):
        self.assertTrue(all(not e.supports_unattended_publishing for e in EMPLOYERS))
        self.assertTrue(all(x.stage=="probe_only" for x in EMPLOYERS[3:]))

    def test_bad_domain_or_non_https_rejected(self):
        with self.assertRaises(ValueError):
            Employer("Fake","http://fake.example/jobs","fake.example","custom","probe_only")
        with self.assertRaises(ValueError):
            Employer("Fake","https://jobs.fake.example/test","elsewhere.example","custom","shadow")
        with self.assertRaises(ValueError):
            Employer("Fake","https://fake.example/jobs","fake.example","custom","live")

    def test_fingerprint_is_not_job_verification(self):
        self.assertEqual(fingerprint('<img src="https://rmkcdn.successfactors.com/a.png">'),"successfactors-like")
        self.assertEqual(fingerprint('<script src="https://careers.example/myworkdayjobs.com"></script>'),"workday-like")
        self.assertEqual(fingerprint('<h1>Company Careers</h1>'),"custom-or-unrecognized")
        self.assertEqual(fingerprint('{"jobs":[]}',"application/json"),"unknown")

if __name__=="__main__":
    unittest.main()
