import os,sys,unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import whatsapp_channel_relay as m

class WAHAChannelBridgeTests(unittest.TestCase):
 def setUp(self):
  self.now=datetime(2026,11,22,12,tzinfo=timezone.utc)
  self.page="jobs/example-software-junior-developer.html"
  self.job={"page":self.page,"company":"Example Software","role":"Junior Developer",
   "loc":"Bengaluru","expYears":"0–1 years","field":"it","batch":"2026",
   "status":"active","salary":"Not Disclosed"}
  self.tg={"one":{"status":"delivered","channel":"@HD_Careers","messageId":727,
   "page":self.page,"deliveredAt":self.now.isoformat()}}
  self.initial={"version":1,"activationAt":(self.now-timedelta(hours=1)).isoformat(),"items":{}}
 def test_activation_no_backfill(self):
  ledger={"version":1,"activationAt":None,"items":{}}
  self.assertIsNone(m.select(ledger,self.tg,{self.page:self.job},self.now.isoformat(),"r1"))
  self.assertEqual(ledger["activationAt"],self.now.isoformat())
 def test_confirmed_receipt_claimed(self):
  self.assertEqual(m.select(self.initial,self.tg,{self.page:self.job},self.now.isoformat(),"r2"),self.page)
  self.assertEqual(self.initial["items"][self.page]["status"],"sending")
  self.assertEqual(self.initial["items"][self.page]["claimId"],"r2")
 def test_duplicate_post_not_claimed(self):
  self.initial["items"][self.page]={"status":"provider_accepted"}
  self.assertIsNone(m.select(self.initial,self.tg,{self.page:self.job},self.now.isoformat(),"r3"))
 def test_ambiguous_sending_claim_not_retried(self):
  self.initial["items"][self.page]={"status":"uncertain"}
  self.assertIsNone(m.select(self.initial,self.tg,{self.page:self.job},self.now.isoformat(),"r3"))
 def test_expired_job_held(self):
  self.assertIsNone(m.select(self.initial,self.tg,{self.page:dict(self.job,status="expired")},self.now.isoformat(),"r4"))
  self.assertEqual(self.initial["items"][self.page]["status"],"skipped_inactive")
 def test_no_telegram_message_id(self):
  self.tg["one"].pop("messageId")
  self.assertIsNone(m.select(self.initial,self.tg,{self.page:self.job},self.now.isoformat(),"r5"))
 def test_no_other_channel(self):
  self.tg["one"]["channel"]="@OtherChannel"
  self.assertIsNone(m.select(self.initial,self.tg,{self.page:self.job},self.now.isoformat(),"r5"))
 def test_non_admin_cannot_post(self):
  cid="120363171744447809@newsletter"
  self.assertTrue(m.admin_status([{"id":cid,"role":"ADMIN"}],cid))
  self.assertTrue(m.admin_status([{"id":cid,"role":"OWNER"}],cid))
  self.assertFalse(m.admin_status([{"id":cid,"role":"SUBSCRIBER"}],cid))
  self.assertFalse(m.admin_status([{"id":"1234567890@newsletter","role":"ADMIN"}],cid))
 def test_correct_waha_endpoint_and_payload(self):
  self.assertEqual(m.configured_session(),"default")
  self.assertTrue(m.CHANNEL_RE.fullmatch("120363171744447809@newsletter"))
  self.assertFalse(m.CHANNEL_RE.fullmatch("120363171744447809@c.us"))
 def test_provider_id_strings_or_objects(self):
  self.assertEqual(m.provider_message_id({"id":"true_123@newsletter_ABC"}),"true_123@newsletter_ABC")
  self.assertEqual(m.provider_message_id({"id":{"_serialized":"true_123@newsletter_ABC"}}),"true_123@newsletter_ABC")
  self.assertIsNone(m.provider_message_id({"ack":1}))
 def test_owner_approved_brillio_hiring_alert_exact(self):
  brillio={
   "company":"Brillio",
   "role":"Associate Engineer, Applications & Platforms",
   "loc":"Chennai, Tamil Nadu, India",
   "expYears":"Entry level; up to 2 years",
   "field":"it",
   "page":"jobs/brillio-associate-engineer-applications-platforms.html",
  }
  expected="\n".join([
   "🚨 *BRILLIO HIRING*",
   "",
   "💼 Role: Associate Engineer, Applications & Platforms",
   "📍 Location: Chennai, Tamil Nadu, India",
   "🎓 Experience: Entry level; up to 2 years",
   "💻 Category: IT",
   "",
   "🔗 Apply Link: https://hdcareers.in/jobs/brillio-associate-engineer-applications-platforms.html",
   "",
   "💚 WhatsApp: https://whatsapp.com/channel/0029VbAxOna7NoZvhuKX362z",
   "✈️ Telegram: https://t.me/HD_Careers",
  ])
  self.assertEqual(m.fmt(brillio),expected)
 def test_verified_job_details_and_short_footer(self):
  actual=m.fmt(self.job)
  self.assertTrue(actual.startswith("🚨 *EXAMPLE SOFTWARE HIRING*"))
  self.assertIn("💼 Role: Junior Developer",actual)
  self.assertIn("📍 Location: Bengaluru",actual)
  self.assertIn("🎓 Experience: 0–1 years",actual)
  self.assertIn("💻 Category: IT",actual)
  self.assertIn("🔗 Apply Link: https://hdcareers.in/"+self.page,actual)
  self.assertIn("💚 WhatsApp: https://whatsapp.com/channel/0029VbAxOna7NoZvhuKX362z",actual)
  self.assertIn("✈️ Telegram: https://t.me/HD_Careers",actual)
  self.assertNotIn("Qualification:",actual)
  self.assertNotIn("Package:",actual)
  self.assertNotIn("Application status can change",actual)
 def test_category_only_from_declared_classification(self):
  self.assertEqual(m.job_category({"field":"it"}),"IT")
  self.assertEqual(m.job_category({"field":"nonit"}),"Non-IT")
  self.assertEqual(m.job_category({"cat":"apprenticeship"}),"Apprenticeship")
  self.assertEqual(m.job_category({"categories":["internship"]}),"Internship")
  self.assertEqual(m.job_category({"field":"unknown","cat":"unknown"}),"Not specified")
 def test_fresher_experience_without_invented_numbers(self):
  job=dict(self.job,expYears="Not specified",expType="fresher")
  self.assertIn("🎓 Experience: Freshers eligible",m.fmt(job))
 def test_traversal_page_rejected(self):
  with self.assertRaises(ValueError):m.fmt(dict(self.job,page="../../private"))
 def test_requires_https_no_redirect_to_another_host(self):
  old=os.environ.get("WAHA_BASE_URL")
  try:
   os.environ["WAHA_BASE_URL"]="http://example.com"
   with self.assertRaises(RuntimeError):m.configured_endpoint()
   os.environ["WAHA_BASE_URL"]="https://waha.example.com"
   self.assertEqual(m.configured_endpoint(),"https://waha.example.com")
  finally:
   if old is None:os.environ.pop("WAHA_BASE_URL",None)
   else:os.environ["WAHA_BASE_URL"]=old
if __name__=="__main__":unittest.main()
