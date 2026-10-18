"""Tests for deployment-gated Telegram hourly scheduling (offline, no sends)."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import hourly_telegram as h

class HourlyTelegramTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        (root/"data").mkdir()
        self.ctx = patch.multiple(h, ROOT=root, QUEUE=root/"data"/"telegram-hourly-queue.json",
                                   LEDGER=root/"data"/"telegram-deliveries.json",
                                   MANIFEST=root/"data"/"telegram-approved-batch.json",
                                   JOBS=root/"data"/"jobs.json")
        self.ctx.start()
        self.addCleanup(self.ctx.stop)
        self.env = patch.dict(os.environ, {"GITHUB_RUN_ID": "7777"}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        pages = ["jobs/test-%02d.html" % i for i in range(10)]
        h.save(h.JOBS, [{"page": page, "status": "active"} for page in pages])
        h.save(h.MANIFEST, {"approved": True, "batchId": "admin-7777", "pages": pages})
        h.save(h.LEDGER, {})
        h.save(h.QUEUE, {"version": 1, "intervalMinutes": 60, "items": []})
        self.event = root/"event.json"
        h.save(self.event, {"client_payload": {"telegramDeliveryMode": "hourly"}})

    def test_first_job_immediate_and_followups_hourly(self):
        h.enqueue(self.event)
        self.assertEqual(len(h.queue()["items"]), 10)
        t = datetime(2026, 10, 18, 4, 30, tzinfo=timezone.utc)
        with patch.object(h, "datetime") as clock:
            clock.now.return_value = t
            h.claim(prime=True, now=t)
        q = h.queue()
        self.assertEqual(q["items"][0]["status"], "sending")
        self.assertTrue(all(x["status"] == "pending" for x in q["items"][1:]))
        # Simulate Telegram confirmation and release the following nine.
        q["items"][0].update(status="delivered", deliveredAt=h.stamp(t), messageId=100)
        h.refresh_due(q)
        h.save(h.QUEUE, q)
        self.assertEqual(h.parse(q["items"][1]["dueAt"]), t + timedelta(hours=1))
        self.assertEqual(h.parse(q["items"][9]["dueAt"]), t + timedelta(hours=9))
        h.claim(now=t + timedelta(minutes=59))
        self.assertFalse(any(x["status"] == "sending" for x in h.queue()["items"]))
        h.claim(now=t + timedelta(hours=1))
        self.assertEqual(h.queue()["items"][1]["status"], "sending")

    def test_no_second_prime_or_duplicate_claim(self):
        h.enqueue(self.event)
        h.claim(prime=True)
        h.claim(prime=True)
        self.assertEqual(sum(x["status"] == "sending" for x in h.queue()["items"]), 1)

    def test_safe_merge_never_downgrades_delivered_receipt(self):
        h.enqueue(self.event)
        q = h.queue()
        q["items"][0].update(status="delivered", deliveredAt=h.stamp(), messageId=222)
        h.save(h.QUEUE, q)
        snapshot = h.QUEUE.parent/"older.json"
        older = json.loads(json.dumps(q))
        older["items"][0].update(status="pending", messageId=None)
        h.save(snapshot, older)
        h.merge(snapshot)
        self.assertEqual(h.queue()["items"][0]["messageId"], 222)
        self.assertEqual(h.queue()["items"][0]["status"], "delivered")

    def test_relay_arms_at_actual_delivered_plus_60m_without_sending(self):
        h.enqueue(self.event)
        now = datetime(2026, 10, 18, 8, 0, tzinfo=timezone.utc)
        q = h.queue()
        q["items"][0].update(status="delivered", deliveredAt=h.stamp(now), messageId=521)
        h.save(h.QUEUE, q)
        output_file = h.QUEUE.parent/"next-output"
        with patch.dict(os.environ, {"GITHUB_OUTPUT": str(output_file)}, clear=False):
            h.next_wakeup(now=now+timedelta(minutes=4))
        outputs = dict(line.split("=", 1) for line in output_file.read_text().splitlines())
        self.assertEqual(outputs["armed"], "true")
        self.assertEqual(int(outputs["delay_seconds"]), 56*60)
        self.assertEqual(h.parse(outputs["next_due"]), now+timedelta(hours=1))
        self.assertTrue(all(x.get("status") != "sending" for x in h.queue()["items"]))

    def test_relay_never_resends_an_uncertain_or_inflight_claim(self):
        h.enqueue(self.event)
        now = datetime(2026, 10, 18, 8, 0, tzinfo=timezone.utc)
        q = h.queue()
        q["items"][0].update(status="sending",claimId="earlier")
        h.save(h.QUEUE,q)
        p=h.QUEUE.parent/"relay-stop"
        with patch.dict(os.environ, {"GITHUB_OUTPUT": str(p)}, clear=False):
            h.next_wakeup(now=now)
        self.assertIn("armed=false",p.read_text())
        q=h.queue()
        q["items"][0].update(status="uncertain")
        q["items"][1].update(status="uncertain")
        for item in q["items"][2:]:
            item.update(status="uncertain")
        h.save(h.QUEUE,q)
        p.unlink()
        with patch.dict(os.environ, {"GITHUB_OUTPUT": str(p)}, clear=False):
            h.next_wakeup(now=now)
        self.assertIn("armed=false",p.read_text())

    def test_relay_due_is_zero_when_cron_has_already_missed_due_time(self):
        h.enqueue(self.event)
        t=datetime(2026,10,18,4,0,tzinfo=timezone.utc)
        q=h.queue()
        q["items"][0].update(status="delivered",messageId=700,deliveredAt=h.stamp(t))
        h.save(h.QUEUE,q)
        out=h.QUEUE.parent/"relay-due"
        with patch.dict(os.environ,{"GITHUB_OUTPUT":str(out)},clear=False):
            h.next_wakeup(now=t+timedelta(hours=3))
        self.assertIn("delay_seconds=0",out.read_text())

    def test_one_off_vip_does_not_enqueue(self):
        h.save(h.MANIFEST, {"approved": True, "batchId": "admin-7777", "pages": ["jobs/test-00.html"]})
        h.save(self.event, {"client_payload": {"telegramDeliveryMode": "instant"}})
        h.enqueue(self.event)
        self.assertFalse(h.queue()["items"])

if __name__ == "__main__":
    unittest.main()
