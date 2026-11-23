"""Offline safety tests for the Whapi.Cloud Channel relay (no live messages)."""
import os
import sys
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import whapi_channel_relay as m


class WhapiChannelRelayTests(unittest.TestCase):
    def setUp(self):
        self.cid = "120363171744447809@newsletter"

    def test_exact_admin_or_owner_role(self):
        self.assertTrue(m.admin_status({"id": self.cid, "user_role": "admin"}, self.cid))
        self.assertTrue(m.admin_status({"id": self.cid, "role": "owner"}, self.cid))
        self.assertTrue(m.admin_status({"newsletter": {"id": self.cid, "role": "ADMIN"}}, self.cid))
        self.assertFalse(m.admin_status({"id": self.cid, "role": "subscriber"}, self.cid))
        self.assertFalse(m.admin_status({"id": "1234567890@newsletter", "role": "admin"}, self.cid))
        self.assertFalse(m.admin_status({"id": self.cid}, self.cid))

    def test_channel_id_requires_internal_jid(self):
        with patch.dict(os.environ, {"WHAPI_CHANNEL_ID": self.cid}):
            self.assertEqual(m.channel_id(), self.cid)
        with patch.dict(os.environ, {"WHAPI_CHANNEL_ID": "https://whatsapp.com/channel/123"}):
            with self.assertRaises(ValueError):
                m.channel_id()

    def test_message_id_is_required_and_not_a_delivery_proof(self):
        self.assertEqual(m.message_id({"sent": True, "message": {"id": "abc123"}}), "abc123")
        self.assertEqual(m.message_id({"id": {"_serialized": "msg123"}}), "msg123")
        self.assertIsNone(m.message_id({"sent": False, "message": {"id": "abc123"}}))
        self.assertIsNone(m.message_id({"status": "pending"}))
        self.assertIsNone(m.message_id({"message": []}))

    def test_no_live_calls_when_disabled(self):
        with patch.dict(os.environ, {"WHAPI_CHANNEL_ENABLED": "false"}):
            with self.assertRaises(RuntimeError):
                m.must_be_enabled()
        with patch.dict(os.environ, {"WHAPI_CHANNEL_ENABLED": "true",
                                     "WAHA_CHANNEL_ENABLED": "true"}):
            with self.assertRaises(RuntimeError):
                m.must_be_enabled()
        with patch.dict(os.environ, {"WHAPI_CHANNEL_ENABLED": "true",
                                     "WAHA_CHANNEL_ENABLED": "false"}):
            m.must_be_enabled()

    def test_one_whatsapp_post_per_sixty_minutes_even_after_telegram_burst(self):
        start = datetime(2026, 11, 24, 3, 35, tzinfo=timezone.utc)
        pages = [f"jobs/fresher-{i}.html" for i in range(3)]
        jobs = {p: {"page":p,"status":"active"} for p in pages}
        tg = {str(i): {"page":p,"status":"delivered","channel":"@HD_Careers",
                       "messageId":500+i,"deliveredAt":(start+timedelta(seconds=i)).isoformat()}
              for i,p in enumerate(pages)}
        doc = {"version":1,"activationAt":(start-timedelta(hours=2)).isoformat(),"items":{}}
        one=m.claim_limited(doc,tg,jobs,(start+timedelta(minutes=1)).isoformat(),"first")
        self.assertEqual(one,pages[0])
        doc["items"][one].update(status="provider_accepted",
                                 acceptedAt=(start+timedelta(minutes=1)).isoformat())
        self.assertIsNone(m.claim_limited(doc,tg,jobs,(start+timedelta(minutes=59)).isoformat(),"too-early"))
        self.assertNotIn(pages[1],doc["items"])
        two=m.claim_limited(doc,tg,jobs,(start+timedelta(minutes=61)).isoformat(),"second")
        self.assertEqual(two,pages[1])
        doc["items"][two].update(status="provider_accepted",
                                 acceptedAt=(start+timedelta(minutes=61)).isoformat())
        self.assertIsNone(m.claim_limited(doc,tg,jobs,(start+timedelta(minutes=90)).isoformat(),"early3"))
        self.assertEqual(m.claim_limited(doc,tg,jobs,(start+timedelta(minutes=122)).isoformat(),"third"),pages[2])

    def test_old_todays_backlog_not_mirrored_tomorrow(self):
        today=datetime(2026,11,24,3,40,tzinfo=timezone.utc)
        yesterday=today-timedelta(days=1)
        old="jobs/old-post.html"
        fresh="jobs/new-post.html"
        jobs={p:{"page":p,"status":"active"} for p in (old,fresh)}
        tg={"yesterday":{"page":old,"status":"delivered","channel":"@HD_Careers",
                          "messageId":770,"deliveredAt":yesterday.isoformat()},
            "today":{"page":fresh,"status":"delivered","channel":"@HD_Careers",
                     "messageId":771,"deliveredAt":today.isoformat()}}
        doc={"version":1,"activationAt":(yesterday-timedelta(days=2)).isoformat(),"items":{}}
        picked=m.claim_limited(doc,tg,jobs,(today+timedelta(minutes=2)).isoformat(),"run")
        self.assertEqual(picked,fresh)
        self.assertEqual(doc["items"][old]["status"],"skipped_previous_day")

    def test_precommitted_inflight_wa_blocks_new_claim(self):
        t=datetime(2026,11,24,3,30,tzinfo=timezone.utc)
        doc={"version":1,"activationAt":(t-timedelta(days=1)).isoformat(),
             "items":{"jobs/first.html":{"status":"sending","claimId":"previous"}}}
        tg={"1":{"page":"jobs/other.html","status":"delivered","channel":"@HD_Careers",
                 "messageId":123,"deliveredAt":t.isoformat()}}
        self.assertIsNone(m.claim_limited(doc,tg,{"jobs/other.html":{"page":"jobs/other.html","status":"active"}},t.isoformat(),"new"))

    def test_untrusted_path_rejected(self):
        with self.assertRaises(ValueError):
            m.api("//evil.example/messages/text")

    def test_admin_verification_uses_exact_jid_without_sending(self):
        with patch.dict(os.environ, {"WHAPI_CHANNEL_ID": self.cid}):
            with patch.object(m, "api", return_value={"id": self.cid, "user_role": "owner"}) as f:
                m.verify_admin()
                f.assert_called_once_with("/newsletters/" + self.cid)
        with patch.dict(os.environ, {"WHAPI_CHANNEL_ID": self.cid}):
            with patch.object(m, "api", return_value={"id": self.cid, "user_role": "subscriber"}):
                with self.assertRaises(RuntimeError):
                    m.verify_admin()


if __name__ == "__main__":
    unittest.main()
