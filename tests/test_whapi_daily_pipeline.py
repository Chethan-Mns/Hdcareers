"""Offline contract for the ten-job daily WhatsApp mirror. No API calls."""
import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import whatsapp_channel_relay as shared
import whapi_channel_relay as m


class WhapiDailyPipelineTests(unittest.TestCase):
    def setUp(self):
        self.base = datetime(2026, 11, 24, 3, 30, tzinfo=timezone.utc)
        self.start = self.base - timedelta(hours=2)
        self.doc = {"version": 1, "activationAt": self.start.isoformat(), "items": {}}
        self.tg = {}
        self.jobs = {}
        for i in range(1, 13):
            page = f"jobs/verified-job-{i:02d}.html"
            stamp = self.base + timedelta(minutes=i)
            self.tg[str(i)] = {
                "status": "delivered",
                "channel": "@HD_Careers",
                "messageId": i,
                "page": page,
                "deliveredAt": stamp.isoformat(),
            }
            self.jobs[page] = {"page": page, "company": "Test Company",
                               "role": "Junior Developer", "status": "active"}

    def test_max_ten_per_ist_day(self):
        claims = []
        for i in range(10):
            at=(self.base+timedelta(minutes=15,hours=i)).isoformat()
            page = m.claim_limited(self.doc, self.tg, self.jobs,
                                   at, f"run{i}")
            self.assertIsNotNone(page)
            claims.append(page)
            self.doc["items"][page].update(status="provider_accepted",acceptedAt=at)
        self.assertEqual(len(set(claims)), 10)
        self.assertIsNone(m.claim_limited(self.doc, self.tg, self.jobs,
                     (self.base+timedelta(minutes=15,hours=10)).isoformat(), "next"))
        self.assertEqual(sum(v["status"] == "skipped_daily_cap"
                             for v in self.doc["items"].values()), 2)

    def test_skip_unverified_not_counted_in_quota(self):
        first = m.claim_limited(self.doc, self.tg, self.jobs,
                                (self.base+timedelta(minutes=15)).isoformat(), "1")
        self.doc["items"][first]["status"] = "skipped_unverified"
        for i in range(10):
            at=(self.base+timedelta(minutes=15,hours=i)).isoformat()
            page = m.claim_limited(self.doc, self.tg, self.jobs,
                                   at, f"run{i+2}")
            self.assertIsNotNone(page)
            self.doc["items"][page].update(status="provider_accepted",acceptedAt=at)
        self.assertEqual(sum(v["status"] == "provider_accepted"
                             for v in self.doc["items"].values()), 10)

    def test_test_posts_not_reposted(self):
        used = "jobs/verified-job-01.html"
        self.doc["items"][used] = {
            "status": "provider_accepted", "testOnly": True,
            "telegramDeliveredAt": self.tg["1"]["deliveredAt"],
            "channelId": m.APPROVED_CHANNEL,
        }
        next_page = m.claim_limited(self.doc, self.tg, self.jobs,
                                    self.base.isoformat(), "next")
        self.assertEqual(next_page, "jobs/verified-job-02.html")

    def test_activation_never_replays_old_telegram(self):
        self.doc["activationAt"] = None
        self.assertIsNone(m.claim_limited(self.doc, self.tg, self.jobs,
                                          self.base.isoformat(), "fresh"))
        self.assertEqual(self.doc["items"], {})
        self.assertEqual(self.doc["activationAt"], self.base.isoformat())

    def test_ist_calendar_boundary(self):
        self.assertEqual(m.telegram_ist_day("2026-11-22T18:31:00+00:00"), "2026-11-23")

    def test_channel_is_only_owner_selected_channel(self):
        self.assertEqual(m.APPROVED_CHANNEL, "120363419928883930@newsletter")
        with patch.dict(os.environ, {"WHAPI_CHANNEL_ID": "120363328521456313@newsletter",
                                     "WHAPI_CHANNEL_ENABLED": "true"}):
            with self.assertRaises(RuntimeError):
                m.channel_id()

    def test_workflow_keeps_existing_first_and_hourly_telegram_sends(self):
        admin = (ROOT / ".github/workflows/admin-job-generator.yml").read_text()
        hourly = (ROOT / ".github/workflows/hourly-telegram-queue.yml").read_text()
        mirror = (ROOT / ".github/workflows/whapi-channel-mirror.yml").read_text()
        self.assertIn("scripts/hourly_telegram.py prime", admin)
        self.assertIn("scripts/hourly_telegram.py send", admin)
        self.assertIn("gh workflow run whapi-channel-mirror.yml", admin)
        self.assertIn("gh workflow run whapi-channel-mirror.yml", hourly)
        self.assertIn("scripts/whapi_channel_relay.py claim", mirror)
        self.assertIn("scripts/whapi_channel_relay.py send", mirror)
        self.assertIn("WHAPI_CHANNEL_ENABLED: \"true\"", mirror)

    def test_configuration_and_safe_quota(self):
        cfg = json.loads((ROOT / "data/whapi-channel-config.json").read_text())
        self.assertEqual(cfg["channelId"], m.APPROVED_CHANNEL)
        self.assertEqual(cfg["maxPostsPerDay"], m.MAX_DAILY_POSTS)
        self.assertEqual(cfg["maxPostsPerDay"], 10)


if __name__ == "__main__":
    unittest.main()
