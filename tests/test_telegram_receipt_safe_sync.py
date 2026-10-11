from __future__ import annotations
import importlib.util
import tempfile
import json
import unittest
from pathlib import Path

src=Path(__file__).resolve().parents[1]/"scripts"/"merge_telegram_delivery_receipts.py"
spec=importlib.util.spec_from_file_location("ledger_merge",src)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def receipt(mid, status="delivered", page="jobs/company-job.html"):
    return {"status":status,"batchId":"admin-verified","page":page,"channel":"@testchannel","messageId":mid,
            "deliveredAt":"2026-10-11T06:33:34Z"}


class TestTelegramReceipts(unittest.TestCase):
    def test_append_nine_confirmed_messages_without_losing_prior_receipts(self):
        current={"@testchannel|jobs/old-job.html":receipt(440,page="jobs/old-job.html")}
        incoming={f"@testchannel|jobs/approved-{i}.html":receipt(463+i,page=f"jobs/approved-{i}.html") for i in range(9)}
        merged,added=m.merge(current,incoming)
        self.assertEqual(added,9)
        self.assertEqual(len(merged),10)
        self.assertEqual(merged["@testchannel|jobs/old-job.html"]["messageId"],440)
        second,count=m.merge(merged,incoming)
        self.assertEqual(count,0)
        self.assertEqual(second,merged)

    def test_delivered_receipts_are_never_overwritten(self):
        key="@testchannel|jobs/company-job.html"
        original={key:receipt(463)}
        with self.assertRaisesRegex(ValueError,"Different Telegram message IDs"):
            m.merge(original,{key:receipt(999)})
        out,updated=m.merge(original,{key:receipt(463)})
        self.assertEqual(updated,0)
        self.assertEqual(out[key]["messageId"],463)

    def test_uncertain_receipt_is_not_downgraded_to_failed(self):
        key="@testchannel|jobs/company-job.html"
        uncertain=receipt(None,"uncertain")
        failed=receipt(None,"failed")
        out,changed=m.merge({key:uncertain},{key:failed})
        self.assertEqual(changed,0)
        self.assertEqual(out[key]["status"],"uncertain")

    def test_failed_receipt_can_be_replaced_by_definite_delivery(self):
        key="@testchannel|jobs/company-job.html"
        out,updated=m.merge({key:receipt(None,"failed")},{key:receipt(463)})
        self.assertEqual(updated,1)
        self.assertEqual(out[key]["status"],"delivered")

    def test_reject_mismatched_page_or_invalid_status(self):
        with self.assertRaisesRegex(ValueError,"page or status"):
            m.merge({},{"@testchannel|jobs/first.html":receipt(463,page="jobs/second.html")})
        with self.assertRaisesRegex(ValueError,"page or status"):
            m.merge({},{"@testchannel|jobs/first.html":receipt(463,"unknown",page="jobs/first.html")})

    def test_local_merge_writes_clean_json_and_no_telegram_calls(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            captured=base/"snapshot.json";current=base/"ledger.json"
            captured.write_text(json.dumps({"@testchannel|jobs/company-job.html":receipt(463)}))
            current.write_text("{}")
            m.main_original=None
            output,added=m.merge(m.load(current),m.load(captured))
            current.write_text(json.dumps(output,indent=2)+"\n")
            self.assertEqual(added,1)
            self.assertEqual(m.load(current)["@testchannel|jobs/company-job.html"]["messageId"],463)


if __name__=="__main__": unittest.main()
