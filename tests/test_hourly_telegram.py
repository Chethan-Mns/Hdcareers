import importlib.util
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("hourly_telegram",HERE/"scripts/hourly_telegram.py")
hourly=importlib.util.module_from_spec(spec)
spec.loader.exec_module(hourly)

class HourlyTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        root=Path(self.temp.name)
        self.patchers=[patch.object(hourly,"QUEUE",root/"queue.json"),patch.object(hourly,"LEDGER",root/"ledger.json"),
                       patch.object(hourly,"MANIFEST",root/"manifest.json"),patch.object(hourly,"JOBS",root/"jobs.json")]
        for p in self.patchers:p.start()
        self.event=root/"event.json"
        hourly.save(hourly.JOBS,[{"page":"jobs/ergomed.html"},{"page":"jobs/skild.html"}])
        hourly.save(hourly.MANIFEST,{"approved":True,"batchId":"admin-123","pages":["jobs/ergomed.html","jobs/skild.html"]})
        hourly.save(hourly.LEDGER,{})

    def tearDown(self):
        for p in reversed(self.patchers):p.stop()
        self.temp.cleanup()

    def test_enqueue_requires_exact_run_and_hourly_mode(self):
        hourly.save(self.event,{"client_payload":{"telegramDeliveryMode":"instant"}})
        with patch.dict(os.environ,{"GITHUB_RUN_ID":"123"}):
            hourly.enqueue(self.event)
        self.assertEqual(hourly.queue()["items"],[])
        hourly.save(self.event,{"client_payload":{"telegramDeliveryMode":"hourly"}})
        with patch.dict(os.environ,{"GITHUB_RUN_ID":"321"}):
            hourly.enqueue(self.event)
        self.assertEqual(hourly.queue()["items"],[])
        with patch.dict(os.environ,{"GITHUB_RUN_ID":"123"}):
            hourly.enqueue(self.event)
            hourly.enqueue(self.event)
        self.assertEqual(len(hourly.queue()["items"]),2)

    def test_claim_must_be_persisted_before_send_and_never_double_claim(self):
        hourly.save(hourly.QUEUE,{"version":1,"intervalMinutes":60,"items":[
            {"page":"jobs/ergomed.html","batchId":"admin-123","status":"pending"},
            {"page":"jobs/skild.html","batchId":"admin-123","status":"pending"}]})
        with patch.dict(os.environ,{"GITHUB_RUN_ID":"42"}):
            hourly.claim()
            hourly.claim()
        self.assertEqual([x["status"] for x in hourly.queue()["items"]],["sending","pending"])
        with patch.dict(os.environ,{"GITHUB_RUN_ID":"43"}):
            hourly.claim()
        self.assertEqual([x["status"] for x in hourly.queue()["items"]],["sending","pending"])

    def test_wait_an_hour_between_successful_messages(self):
        hourly.save(hourly.QUEUE,{"version":1,"intervalMinutes":60,"items":[
            {"page":"jobs/ergomed.html","status":"delivered","deliveredAt":datetime.now(timezone.utc).isoformat()},
            {"page":"jobs/skild.html","status":"pending"}]})
        with patch.dict(os.environ,{"GITHUB_RUN_ID":"43"}):
            hourly.claim()
        self.assertEqual(hourly.queue()["items"][1]["status"],"pending")
        q=hourly.queue()
        q["items"][0]["deliveredAt"]=(datetime.now(timezone.utc)-timedelta(minutes=61)).isoformat()
        hourly.save(hourly.QUEUE,q)
        with patch.dict(os.environ,{"GITHUB_RUN_ID":"43"}):
            hourly.claim()
        self.assertEqual(hourly.queue()["items"][1]["status"],"sending")

    def test_old_delivery_is_not_reposted(self):
        hourly.save(hourly.QUEUE,{"version":1,"intervalMinutes":60,"items":[
            {"page":"jobs/ergomed.html","status":"pending"},
            {"page":"jobs/skild.html","status":"pending"}]})
        hourly.save(hourly.LEDGER,{"@HD_Careers|jobs/ergomed.html":
            {"status":"delivered","page":"jobs/ergomed.html","messageId":500,"deliveredAt":"2026-10-10T10:00:00Z"}})
        with patch.dict(os.environ,{"GITHUB_RUN_ID":"43"}):
            hourly.claim()
        self.assertEqual(hourly.queue()["items"][0]["status"],"already-delivered")
        self.assertEqual(hourly.queue()["items"][1]["status"],"sending")

if __name__=="__main__":unittest.main()
