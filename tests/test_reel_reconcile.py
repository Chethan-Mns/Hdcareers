import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from reel_reconcile import merge_provider_status,reconcile


class PublicationReconcileTests(unittest.TestCase):
    def setUp(self):
        self.record={"jobId":382,"provider":"superprofile","status":"scheduled",
                     "superprofilePostId":"a"*24}
    def test_published_updates_ledger_from_provider(self):
        post={"igUsername":"hd_careers","status":"published",
              "publish":{"mediaId":"179111","permalink":"https://www.instagram.com/reel/Czzz/"}}
        got=merge_provider_status(self.record,post)
        self.assertEqual(got["status"],"posted")
        self.assertEqual(got["instagramMediaId"],"179111")
    def test_unknown_does_not_claim_posted(self):
        post={"igUsername":"hd_careers","status":"unknown","publish":{}}
        got=merge_provider_status(self.record,post)
        self.assertEqual(got["status"],"uncertain")
    def test_wrong_instagram_account_rejected(self):
        with self.assertRaises(ValueError):
            merge_provider_status(self.record,{"igUsername":"hdcareers","status":"published"})
    def test_failed_does_not_retry(self):
        p={"igUsername":"hd_careers","status":"failed","publish":{"reason":{"title":"Token expired"}}}
        result,n=reconcile([self.record],lambda _:{"post":p})
        self.assertEqual(n,1)
        self.assertEqual(result[0]["status"],"failed")
        self.assertIn("Token",result[0]["publishProblem"])
    def test_provider_outage_preserves_scheduled(self):
        def error(_):raise ValueError("provider offline")
        result,n=reconcile([self.record],error)
        self.assertEqual(n,0)
        self.assertEqual(result,[self.record])


if __name__=="__main__":
    unittest.main()
