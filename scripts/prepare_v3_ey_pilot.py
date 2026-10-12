"""One-job V3 publishing pilot: fail closed unless the official EY requisition is live."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from discovery_v3_shadow import get_official_page,classify_exact

ROOT=Path(__file__).resolve().parents[1]
SEED_ID="1750731"
APPROVAL=ROOT/"data/discovery-v3-ey-pilot-approval.json"
SEEDS=ROOT/"data/discovery-v3-seeds.json"
PUBLISHED=ROOT/"data/jobs.json"
PAGE="jobs/ey-associate-analyst-tax-global-compliance-reporting-mumbai-1750731.html"

def candidate():
    approvals=json.loads(APPROVAL.read_text())
    if approvals.get("approvalId")!="v3-official-ey-pilot-20261012" or approvals.get("jobId")!=SEED_ID or approvals.get("approvedForWebsiteAndTelegram") is not True:
        raise SystemExit("Owner approval manifest is missing or does not match EY 1750731.")
    seed=next((x for x in json.loads(SEEDS.read_text()) if x["company"]=="EY" and x["jobId"]==SEED_ID),None)
    if not seed: raise SystemExit("EY seed not found")
    url=seed["url"]
    if urlparse(url).hostname!="careers.ey.com":raise SystemExit("Non-official job URL")
    jobs=json.loads(PUBLISHED.read_text())
    if any(str(x.get("apply","")).rstrip("/").lower()==url.rstrip("/").lower() for x in jobs):
        raise SystemExit("Job already published: no duplicate delivery allowed.")
    if any(str(x.get("jobId",""))==SEED_ID and str(x.get("company","")).lower()=="ey" for x in jobs):
        raise SystemExit("EY requisition already published under another URL.")
    now=datetime.now(timezone.utc).strftime("%d %b %Y").lstrip("0")
    return seed,{
        "page":PAGE,
        "company":"EY",
        "domain":"careers.ey.com",
        "logo":["EY","#20212b"],
        "salary":"Not Disclosed",
        "role":seed["role"],
        "roleTag":"Associate Analyst – Tax / Global Compliance & Reporting",
        "loc":"Mumbai, Maharashtra, India",
        "locationFilter":"Mumbai",
        "batch":"Not specified",
        "elig":"B.Com degree; the employer's posting specifies 0–1 years of experience. Applicants should have accounting and tax fundamentals relevant to compliance and reporting.",
        "cat":"nonit",
        "expType":"fresher",
        "expYears":"0–1 years",
        "date":"8 Oct 2026",
        "desc":"EY is recruiting an Associate Analyst for Financial Services Tax, Global Compliance and Reporting in Mumbai. The position assists tax professionals with foreign portfolio investor (FPI) tax compliance, reporting inputs, related records and client deliverables. The official job listing asks for a B.Com qualification and 0–1 years of experience. The team supports banking, insurance, investment and wealth-management clients with changing tax compliance requirements.",
        "resp":[
            "Support tax compliance and reporting activities with accuracy and attention to regulatory requirements.",
            "Work with tax data, documentation and reporting inputs used in global compliance processes.",
            "Apply foundational foreign portfolio investor (FPI) tax knowledge to support relevant workflows.",
            "Analyze tax-related information and prepare accurate contributions to client deliverables.",
            "Coordinate with colleagues on cross-border compliance tasks and reporting timelines."
        ],
        "skills":["Tax compliance","Foreign portfolio investor (FPI) taxation","Tax data","Reporting documentation","Accounting basics","Excel","Communication"],
        "apply":url,
        "status":"active",
        "sourceName":"EY official careers – requisition 1750731",
        "verifiedDate":now,
        "who":"B.Com graduates with 0–1 years of relevant experience and an interest in financial-services tax compliance and reporting.",
        "workMode":"Not Specified",
        "jobId":SEED_ID,
        "sourceVerificationMethod":"official-employer-v3-exact-job",
    }

def prepare(output,skip_live_check=False):
    seed,job=candidate()
    if not skip_live_check:
        response=get_official_page(seed["url"],"EY")
        if response["status"]!="ok":
            raise SystemExit("V3 pilot stopped: official employer page unavailable: "+response.get("reason",""))
        result=classify_exact(response["body"],seed["url"],SEED_ID,seed["role"])
        if result["state"]!="live" or not {"matching-title","matching-requisition","apply-control"}.issubset(result["evidence"]):
            raise SystemExit("V3 pilot stopped: current source is not strongly verified Live.")
        job["verificationEvidence"]={"observedAt":datetime.now(timezone.utc).isoformat(),"source":"official EY careers",
          "method":"title+requisition+apply","jobId":SEED_ID}
    payload={"event_type":"admin_publish_jobs","client_payload":{"jobs":[job],"requestId":"v3-official-ey-pilot-20261012"}}
    output.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n")
    print("V3 pilot prepared exactly one new EY job; production pipeline must verify it again.")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("output")
    p.add_argument("--skip-live-check",action="store_true")
    args=p.parse_args()
    prepare(Path(args.output),args.skip_live_check)
