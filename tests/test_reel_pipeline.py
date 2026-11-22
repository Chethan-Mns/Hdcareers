import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from reel_preflight import validate
from superprofile_reel_bridge import exact_dm,matching_draft,unique_key


class ReelPipelineTests(unittest.TestCase):
    def setUp(self):
        self.manifest={
          "jobId":382, "company":"Brillio",
          "role":"Associate Engineer, Applications & Platforms",
          "jobUrl":"https://hdcareers.in/jobs/brillio-associate-engineer-applications-platforms.html",
          "caption":"Brillio hiring fresher Associate Engineer, Applications & Platforms. "
                    "https://hdcareers.in/jobs/brillio-associate-engineer-applications-platforms.html"
        }
        self.status={"status":"rendered","captionSync":"source_word_timestamps",
                     "voiceEngine":"elevenlabs","employerLogoFound":True,
                     "durationSeconds":10.0,"audioCommercialRightsVerified":True}
        self.binding={
          "jobId":382,"jobUrl":self.manifest["jobUrl"],
          "instagramAccount":"hd_careers","postId":"a"*24,"state":"scheduled",
          "autoDm":{"matchMode":"any","delaySeconds":30,"followGate":True}
        }

    def make_video(self,temp):
        p=Path(temp)/"reel.mp4"
        p.write_bytes(b"video"*30000)
        return p

    def test_ready_when_all_conditions_match(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(validate(self.manifest,self.status,self.make_video(d),
                                      commercial_required=True,binding=self.binding,
                                      binding_required=True),[])

    def test_rejects_missing_rights(self):
        with tempfile.TemporaryDirectory() as d:
            errors=validate(self.manifest,dict(self.status,audioCommercialRightsVerified=False),
                            self.make_video(d))
            self.assertTrue(any("commercial" in x.lower() for x in errors))

    def test_rejects_wrong_job_autodm(self):
        with tempfile.TemporaryDirectory() as d:
            bad=dict(self.binding,jobId=999)
            errors=validate(self.manifest,self.status,self.make_video(d),
                            binding=bad,binding_required=True)
            self.assertTrue(any("different job" in x for x in errors))

    def test_rejects_wrong_account_and_delay(self):
        with tempfile.TemporaryDirectory() as d:
            bad=dict(self.binding,instagramAccount="hdcareers",
                     autoDm={"matchMode":"keywords","delaySeconds":60,"followGate":False})
            errors=validate(self.manifest,self.status,self.make_video(d),
                            binding=bad,binding_required=True)
            self.assertGreaterEqual(len(errors),2)

    def test_rejects_unsynced_caption_and_missing_logo(self):
        with tempfile.TemporaryDirectory() as d:
            bad=dict(self.status,captionSync="estimated",employerLogoFound=False)
            errors=validate(self.manifest,bad,self.make_video(d))
            self.assertTrue(any("captions" in x for x in errors))
            self.assertTrue(any("logo" in x for x in errors))

    def test_brillio_autodm_is_any_comment_thirty_seconds_and_exact_url(self):
        d=exact_dm(self.manifest)
        self.assertEqual(d["keywords"]["mode"],"any")
        self.assertEqual(d["primaryDelay"],{"timeValue":30,"timeUnit":"second"})
        self.assertEqual(d["buttons"][0]["url"],self.manifest["jobUrl"])
        self.assertEqual(d["followGate"]["retry"]["onFailure"],"stop")

    def test_reuse_only_correct_account_job_draft(self):
        posts=[
            {"id":"a"*24,"igUserId":"17841468879470378","type":"reel","status":"draft",
             "caption":"Brillio Associate Engineer, Applications & Platforms in Chennai"},
            {"id":"b"*24,"igUserId":"17841478165407878","type":"reel","status":"draft",
             "caption":"Brillio Associate Engineer, Applications & Platforms in Chennai"}
        ]
        self.assertEqual(matching_draft(posts,self.manifest,"17841468879470378")["id"],"a"*24)
        self.assertIsNone(matching_draft(posts,self.manifest,"000000"))

    def test_refuse_multiple_drafts(self):
        posts=[{"id":str(i)*24,"igUserId":"1","type":"reel","status":"draft",
                "caption":self.manifest["jobUrl"]} for i in (1,2)]
        with self.assertRaises(Exception):
            matching_draft(posts,self.manifest,"1")

    def test_unguessable_idempotency_key(self):
        self.assertRegex(unique_key(1795371959451),r"^1795371959451:[a-f0-9]{24}$")


if __name__=="__main__":
    unittest.main()
