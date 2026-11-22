import sys,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import whatsapp_channel_relay as m

class ChannelBridgeTests(unittest.TestCase):
 def setUp(self):
  self.now=datetime(2026,11,22,12,tzinfo=timezone.utc)
  self.page="jobs/example-software-junior-developer.html"
  self.job={"page":self.page,"company":"Example Software","role":"Junior Developer",
   "loc":"Bengaluru","expYears":"0–1 years","field":"it","batch":"2026",
   "status":"active","salary":"Not Disclosed"}
  self.tg={"key":{"status":"delivered","channel":"@HD_Careers","messageId":727,
    "page":self.page,"deliveredAt":self.now.isoformat()}}
 def test_first_run_activates_without_historical_posts(self):
  data={"version":1,"activationAt":None,"items":{}}
  selected=m.select(data,self.tg,{self.page:self.job},self.now.isoformat(),"run1")
  self.assertIsNone(selected)
  self.assertEqual(data["activationAt"],self.now.isoformat())
 def test_future_delivered_receipt_is_claimed(self):
  data={"version":1,"activationAt":(self.now-timedelta(hours=1)).isoformat(),"items":{}}
  selected=m.select(data,self.tg,{self.page:self.job},self.now.isoformat(),"run2")
  self.assertEqual(selected,self.page)
  self.assertEqual(data["items"][self.page]["status"],"sending")
 def test_duplicate_receipt_is_ignored(self):
  data={"version":1,"activationAt":(self.now-timedelta(hours=1)).isoformat(),
    "items":{self.page:{"status":"provider_accepted"}}}
  self.assertIsNone(m.select(data,self.tg,{self.page:self.job},self.now.isoformat(),"run3"))
 def test_expired_job_never_claimed(self):
  data={"version":1,"activationAt":(self.now-timedelta(hours=1)).isoformat(),"items":{}}
  self.assertIsNone(m.select(data,self.tg,{self.page:dict(self.job,status="expired")},self.now.isoformat(),"run4"))
  self.assertEqual(data["items"][self.page]["status"],"skipped_inactive")
 def test_no_delivery_receipt_never_claimed(self):
  data={"version":1,"activationAt":(self.now-timedelta(hours=1)).isoformat(),"items":{}}
  self.tg["key"].pop("messageId")
  self.assertIsNone(m.select(data,self.tg,{self.page:self.job},self.now.isoformat(),"run5"))
 def test_no_other_channel(self):
  data={"version":1,"activationAt":(self.now-timedelta(hours=1)).isoformat(),"items":{}}
  self.tg["key"]["channel"]="@NotHDCareers"
  self.assertIsNone(m.select(data,self.tg,{self.page:self.job},self.now.isoformat(),"run5"))
 def test_admin_must_be_verified(self):
  c="120363171744447809@newsletter"
  self.assertTrue(m.is_admin({"newsletters":[{"id":c,"user_role":"admin"}]},c))
  self.assertFalse(m.is_admin({"newsletters":[{"id":c,"user_role":"subscriber"}]},c))
  self.assertFalse(m.is_admin({"newsletters":[{"id":"100000000000@newsletter","user_role":"admin"}]},c))
 def test_channel_text_uses_hd_careers_url_without_inventing_salary(self):
  msg=m.text_for(self.job)
  self.assertIn("https://hdcareers.in/"+self.page,msg)
  self.assertIn("IT",msg)
  self.assertNotIn("Pay:",msg)
 def test_invalid_page_path_refused(self):
  with self.assertRaises(RuntimeError):
   m.text_for(dict(self.job,page="../../private"))
if __name__=="__main__":unittest.main()
