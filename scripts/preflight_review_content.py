#!/usr/bin/env python3
"""Validate source-backed job content before admin review or publishing."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REQUIRED=("company","role","loc","elig","desc","apply","sourceName")

def inspect(batch):
    findings=[]
    for group in ("priority","backup"):
        for candidate in batch.get(group,[]):
            job=candidate.get("job") or {}
            missing=[name for name in REQUIRED if not str(job.get(name) or "").strip()]
            if not isinstance(job.get("resp"),list) or not any(str(x).strip() for x in job.get("resp",[])):
                missing.append("resp")
            if str(candidate.get("apply") or "")!=str(job.get("apply") or ""):
                missing.append("matching_official_url")
            if not str(job.get("apply") or "").startswith("https://"):
                missing.append("secure_official_url")
            findings.append({"id":candidate.get("id"),"company":candidate.get("company"),"role":candidate.get("role"),
                             "group":group,"readyForVerification":not missing,"missing":missing})
    return {"batchId":batch.get("batchId"),"checkedAt":datetime.now(timezone.utc).isoformat(),
            "total":len(findings),"complete":sum(x["readyForVerification"] for x in findings),
            "needsSourceContent":sum(not x["readyForVerification"] for x in findings),
            "items":findings,
            "policy":"Incomplete source details are held for review; never invent job requirements or mark a job expired."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("batch",nargs="?",default="data/daily-review-batch.json")
    p.add_argument("--output",default="")
    p.add_argument("--require-complete",action="store_true",help="Fail if any job lacks verified required content")
    a=p.parse_args()
    result=inspect(json.loads(Path(a.batch).read_text()))
    if a.output:Path(a.output).write_text(json.dumps(result,indent=2)+"\n")
    print(f"Content preflight: {result['complete']}/{result['total']} complete; {result['needsSourceContent']} need source recovery.")
    for item in result["items"]:
        if item["missing"]:print(f"- {item['company']}: {', '.join(item['missing'])}")
    if a.require_complete and result["needsSourceContent"]:
        raise SystemExit("Content gate blocked incomplete daily shortlist; recover or replace candidates before dispatching to admin.")

if __name__=="__main__":main()
