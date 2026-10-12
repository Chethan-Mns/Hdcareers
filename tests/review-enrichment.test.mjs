import test from "node:test";
import assert from "node:assert/strict";
import {enrichReviewedCandidate} from "../lib/review-enrichment.js";

const source="https://careers.example.com/job/req-400";
const candidate=()=>({
 id:"req-400",company:"Example Technology",role:"Graduate Software Engineer",
 apply:source,reviewedStatus:"live",reviewedAt:"2026-10-12T04:00:00Z",
 job:{company:"Example Technology",role:"Graduate Software Engineer",loc:"Bengaluru",
 apply:source,sourceName:"Example Technology Careers",status:"review"}
});
const extracted=()=>({
 sourceUrl:source,company:"Example Technology",role:"Graduate Software Engineer",
 elig:"Bachelor degree in computer science",desc:"Work on distributed systems based on employer job posting.",
 resp:["Develop distributed services","Test complex systems","Work with engineering teams"],
 extraction:{source:"structured",structuredJobPosting:true,description:true,eligibility:true,responsibilities:true}
});
test("Verified Live job can recover missing source fields without changing review evidence",()=>{
 const saved=candidate(),result=enrichReviewedCandidate(saved,extracted());
 assert.deepEqual(result.recovered,["eligibility","description","responsibilities"]);
 assert.equal(result.complete,true);
 assert.equal(result.candidate.job.status,"active");
 assert.equal(result.candidate.reviewedAt,saved.reviewedAt);
 assert.equal(saved.job.status,"review");
 assert.equal(saved.job.desc,undefined);
});
test("Do not invent content based on fallback or placeholder extraction",()=>{
 const x=extracted();x.extraction.eligibility=false;x.extraction.description=false;x.extraction.responsibilities=false;
 const result=enrichReviewedCandidate(candidate(),x);
 assert.deepEqual(result.recovered,[]);
 assert.equal(result.complete,false);
 assert.equal(result.candidate.job.desc,undefined);
});
test("Never overwrite already verified employer descriptions",()=>{
 const x=candidate();x.job.desc="Confirmed original description";
 const result=enrichReviewedCandidate(x,extracted());
 assert.equal(result.candidate.job.desc,"Confirmed original description");
});
test("Mismatch, missing manual review and expired jobs fail closed",()=>{
 const j=candidate();j.reviewedStatus="expired";
 assert.throws(()=>enrichReviewedCandidate(j,extracted()),/Verify/);
 const j2=candidate(),x2=extracted();x2.company="Other Employer";
 assert.throws(()=>enrichReviewedCandidate(j2,x2),/Employer identity/);
 const x3=extracted();x3.sourceUrl="https://careers.example.com/job/other";
 assert.throws(()=>enrichReviewedCandidate(candidate(),x3),/exact reviewed/);
 const x4=extracted();x4.role="Finance Associate";
 assert.throws(()=>enrichReviewedCandidate(candidate(),x4),/Job title/);
});
