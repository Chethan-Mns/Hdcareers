"""Offline safety tests for the Whapi.Cloud Channel relay (no live messages)."""
import os
import sys
import unittest
from pathlib import Path
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
