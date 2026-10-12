#!/usr/bin/env python3
"""One-time owner-approved October 12 publication, with exact candidate URL and job identity checks."""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
APPROVAL=ROOT/"data/owner-approved-ten-20261012.json"
BATCH=ROOT/"data/daily-review-batch.json"
PUBLISHED=ROOT/"data/jobs.json"
IDS=[
    "ahead-7950d5ca","graviton-8764240002","amex-26014347",
    "gehc-r4043087","erm-r00032044","deloitte-110963",
    "nec-744000152589569","omnidian-e4bd2d30",
    "synopsys-19013","bosch-744000152388899",
]
# Editorial rewrites of the exact employer requisitions, not fabricated hiring requirements.
SOURCE_DETAILS={
"deloitte-110963":{
 "desc":"Deloitte Touche Tohmatsu India LLP is seeking an Analyst in Bengaluru to support Microsoft Dynamics 365 Finance & Operations Supply Chain Management implementations. The role assists consultants in requirements gathering, SCM process configuration, functional documentation, testing, data migration and post-go-live assistance.",
 "resp":["Join requirements workshops and help document supply-chain business needs.","Assist consultants with configuration and execution of D365 Finance & Operations SCM processes.","Prepare Functional Design Documents (FDDs) for agreed processes.","Perform unit tests and System Integration Testing (SIT).","Support User Acceptance Testing (UAT), user training and data migration.","Assist with master-data setup and post-go-live support."],
 "elig":"0–2 years in Microsoft Dynamics 365 Finance & Operations, related ERP end-user experience, or willingness to learn D365 F&O. MBA Supply Chain/Operations, BE Industrial/Production/Mechanical Engineering, or equivalent supply-chain-related education.",
 "skills":["D365 Finance & Operations","Supply Chain Management","Functional requirements","ERP configuration","FDD","SIT","UAT"],
 "workMode":"Not specified"
},
"amex-26014347":{
 "desc":"American Express offers a 12-month apprenticeship in Gurugram with its Global Merchant & Network Services governance and merchant-account operations teams. The apprentice supports merchant-data integrity, operational controls and analytics, working on SQL, Excel and cross-team data quality initiatives.",
 "resp":["Analyze and remediate merchant account data quality issues.","Improve merchant industry-code inventories, guidance and monitoring controls.","Work with process owners on operational improvement and data governance.","Use SQL to extract, transform and analyze information from multiple sources.","Develop advanced Excel reports and models for business insights.","Collaborate with technology teams on data-focused tools, including GenAI-enabled workflows."],
 "elig":"Bachelor’s degree in Technology, Engineering or related STEM discipline, including data science, IT, statistics or mathematics. Recent graduates with up to one year of work experience are eligible. Must commit to a 12-month apprenticeship.",
 "skills":["SQL","Excel","Data quality","Analytics","Communication","Merchant data governance"],
 "workMode":"Hybrid","closingAt":"2026-10-13T04:00:00+05:30","expType":"fresher"
},
"gehc-r4043087":{
 "loc":"Bengaluru, Karnataka, India",
 "desc":"GE HealthCare is recruiting a Graduate Engineer Trainee to support manufacturing and quality activities for its Ultrasound and PCS product lines. The trainee assists with production operations, engineering documentation, calibration, validation, supplier quality and continuous improvement in a medical-device environment.",
 "resp":["Support day-to-day ultrasound and PCS manufacturing operations.","Investigate production-line quality issues and support corrective actions.","Maintain calibration schedules, records and equipment validation reports.","Coordinate with production teams and supplier quality teams on rejected materials.","Update work instructions, device history records and change documentation.","Participate in Kaizen, Poka-Yoke and Lean manufacturing improvements."],
 "elig":"B.E./B.Tech in Electrical, Electronics, Biomedical or Mechanical Engineering; fresh graduates or candidates with up to one year of relevant experience.",
 "skills":["Manufacturing","Quality management","Equipment calibration","Documentation","Kaizen","Poka-Yoke"],
 "cat":"nonit","expType":"fresher","expYears":"Fresh graduate or up to 1 year"
},
"erm-r00032044":{
 "desc":"ERM is hiring a People Services Intern for New Delhi to support its Global Delivery Centre HR Operations services across Asia and ANZ. Work includes HR administration, employee lifecycle transactions, employee-data management, ticket-based queries and HR documentation.",
 "resp":["Respond to employee and manager HR administration requests through approved channels.","Support employee onboarding, transfers and departures.","Track and resolve HR queries using the team ticketing system.","Assist with pre-employment checks and HR documents.","Help maintain employee data and process transactions in Workday under guidance.","Keep HR trackers, correspondence and process records accurate and up to date."],
 "elig":"Employer lists this as a People Services internship. A specific mandatory degree or prior-experience threshold was not stated in the accessible vacancy description; refer to the official application for any further eligibility questions.",
 "skills":["HR operations","Workday","Data accuracy","Employee administration","Communication","MS Office"],
 "cat":"nonit","expType":"fresher","closingAt":"2026-10-29T23:59:00+05:30"
},
"nec-744000152589569":{
 "desc":"NEC Software Solutions India is looking for a Full Stack Software Engineer in Pune to design and improve Java and React web applications. The role spans Spring Boot microservices, REST APIs, React/Next.js interfaces, databases and Agile delivery; the vacancy states a hybrid arrangement with three office days weekly.",
 "resp":["Design and enhance general and specialized application software.","Translate business and user needs into technical solutions.","Develop Java, Spring Boot and Hibernate microservices.","Build React and Next.js user interfaces and integrate REST APIs.","Work with MSSQL or MySQL and application data layers.","Collaborate with Agile teams to test, improve and deliver software."],
 "elig":"B.Tech/B.E. in any specialization or BCA; M.Tech/M.E. in Computers or MCA also listed (postgraduate education is not mandatory). Employer emphasizes hands-on Java, Spring Boot, React, APIs and database skills.",
 "skills":["Java","Spring Boot","Hibernate","React","Next.js","REST APIs","MSSQL","MySQL","Git"],
 "workMode":"Hybrid"
},
"omnidian-e4bd2d30":{
 "desc":"Omnidian is hiring a Software Engineer I/II in Bangalore for its Performance and Financial Products team. The role focuses on software feature implementation, Java full-stack components and Databricks data pipelines supporting the distributed solar and energy-storage business.",
 "resp":["Implement and maintain software features in the Performance and Financial Products team.","Build and enhance Java full-stack applications and services.","Contribute to Databricks data-processing pipelines and integrations.","Participate in collaborative code reviews, debugging and delivery.","Work with engineering and product colleagues to improve software reliability."],
 "elig":"Software Engineer I/II opening in Bangalore. Employer considers engineering experience across different bands; refer to the official form and listing for the role-specific experience assessment.",
 "skills":["Java","Full-stack engineering","SQL","Databricks","Software delivery","Data pipelines"],
 "expType":"experienced","workMode":"Hybrid"
},
"synopsys-19013":{
 "desc":"Synopsys is seeking an ASIC Digital Design Engineer in Hyderabad for verification of high-speed interconnect IP such as PCIe, UCIe and DDR. The role involves UVM testbenches, SystemVerilog assertions, test planning, functional coverage, regression debugging and readiness for silicon delivery.",
 "resp":["Plan and execute ASIC/SoC verification for PCIe, UCIe and DDR IP.","Build reusable UVM agents, sequencers, scoreboards and coverage models.","Write SystemVerilog constrained-random tests and assertions.","Debug simulations and regressions using VCS, Verdi and coverage tools.","Analyze protocol compliance issues, coverage gaps and root causes.","Document verification results and collaborate with design and validation engineers."],
 "elig":"B.Tech or M.Tech in Electronics, VLSI, Electrical Engineering or related discipline; 2+ years in hands-on ASIC/SoC verification, with familiarity with UVM, SystemVerilog and at least one high-speed protocol.",
 "skills":["SystemVerilog","UVM","PCIe","UCIe","DDR","VCS","Verdi","Coverage"],
 "expType":"experienced","expYears":"2+ years"
},
"bosch-744000152388899":{
 "loc":"Bengaluru, Karnataka, India",
 "desc":"Bosch Global Software Technologies is hiring a Hardware Developer in Bengaluru for automotive electronics and PS-DC projects. The role covers low- and high-voltage analog/digital circuit designs, power conversion, BLDC motor-control hardware, PCB layouts, module bring-up and validation.",
 "resp":["Design analog/digital circuits and low-/high-voltage automotive hardware.","Develop BLDC motor-control systems and related electronics.","Apply hardware architecture and PCB layout best practices.","Support automotive ECU hardware module development, board bring-up and debugging.","Perform hardware simulations, worst-case analysis and design verification.","Support testing and compliance activities for 48V systems."],
 "elig":"BE/ME/MTech in Electronics, with more than three years of relevant experience.",
 "skills":["Analog circuits","PCB","Power electronics","BLDC motor control","Automotive ECUs","LTspice","PSpice"],
 "expType":"experienced","expYears":">3 years"
}
}
def fail(message): raise SystemExit("Publication safely blocked: "+message)
def build():
 approval=json.loads(APPROVAL.read_text())
 batch=json.loads(BATCH.read_text())
 if approval.get("id")!="owner-approved-20261012-all-ten" or batch.get("batchId")!="2026-10-12-0900-ist":
  fail("The expected 12 October approved review batch is unavailable")
 ids=approval.get("candidateIds")
 if ids!=IDS or len(set(ids))!=10 or not approval.get("humanConfirmedAllLive"):
  fail("Exact owner-approved ten candidate IDs or live confirmation missing")
 original={str(x["id"]):x for x in batch.get("priority",[])+batch.get("backup",[])}
 published=json.loads(PUBLISHED.read_text())
 existing={str(x.get("apply","")).rstrip("/").lower() for x in published}
 now=datetime.now(timezone.utc)
 date=now.strftime("%d %b %Y").lstrip("0")
 prepared=[]
 seen=set()
 for id in IDS:
  if id not in original: fail("Approved candidate missing: "+id)
  candidate=original[id]
  src=dict(candidate.get("job") or {})
  url=str(candidate.get("apply") or "")
  company=str(candidate.get("company") or "")
  role=str(candidate.get("role") or "")
  if src.get("apply")!=url or src.get("company")!=company or src.get("role")!=role:
   fail("Employer, title or exact official URL changed for "+id)
  if not url.startswith("https://") or not urlsplit(url).hostname: fail("Invalid employer URL for "+id)
  if url.rstrip("/").lower() in existing: fail("Job already published, abort to avoid duplicates: "+id)
  if company.casefold() in seen: fail("Duplicate employer: "+company)
  seen.add(company.casefold())
  src.update(SOURCE_DETAILS.get(id,{}))
  missing=[key for key in ("company","role","loc","elig","desc","apply","sourceName") if not src.get(key)]
  if missing or not isinstance(src.get("resp"),list) or not src["resp"]:
   fail(id+" has incomplete official-job content: "+",".join(missing))
  src.update({
   "page":"jobs/"+re.sub(r"[^a-z0-9]+","-",company.lower()+"-"+role.lower()).strip("-")[:90]+".html",
   "domain":urlsplit(url).hostname.removeprefix("www."),
   "logo":[ "".join(w[0] for w in company.split()[:2]).upper(),"#0b6fe8"],
   "salary":"Not disclosed",
   "roleTag":role,"locationFilter":src["loc"],
   "batch":str(src.get("batch") or "Not specified"),
   "date":str(src.get("date") or "Not specified"),
   "verifiedDate":date,"status":"active",
   "who":"Applicants who meet the employer's stated eligibility and role-specific requirements; read the official job posting before applying.",
   "workMode":str(src.get("workMode") or "Not specified"),
   "manualLiveVerifiedAt":now.isoformat(),
   "manualLiveVerifiedUrl":url,
   "browserVerifiedAt":now.isoformat(),
   "sourceReview":"Owner explicitly confirmed this exact job is live and accepting applications on 12 Oct 2026.",
   "skills":list(src.get("skills") or []),
  })
  src["cat"]=src.get("cat") if src.get("cat") in {"it","nonit","internship","apprenticeship","experienced","campus","govt"} else "nonit"
  src["expType"]=src.get("expType") if src.get("expType") in {"fresher","experienced","not-specified"} else "not-specified"
  src["expYears"]=str(src.get("expYears") or "Not specified")
  prepared.append(src)
 if len(prepared)!=10: fail("Wrong job count")
 return {"event_type":"admin_publish_jobs","client_payload":{"jobs":prepared,
   "reviewBatchId":batch["batchId"],"reviewCandidateIds":IDS,"requestId":approval["id"]}}
if __name__=="__main__":
 if len(sys.argv)!=2: fail("Usage: prepare_owner_approved_ten_20261012.py <output-event-file>")
 obj=build()
 Path(sys.argv[1]).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("Prepared exactly 10 owner-approved job drafts; none were published at this step.")
