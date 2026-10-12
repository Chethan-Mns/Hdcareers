import test from "node:test";
import assert from "node:assert/strict";
import {evidenceScore,reprioritizeBeforeReview} from "../lib/review-ranking.js";
const candidate=(i,reason,reviewedStatus="unreviewed")=>({
 id:String(i),company:"Employer "+i,role:"Software Engineer",cat:"it",
 verificationReason:reason,reviewedStatus,
 job:{company:"Employer "+i,loc:"Hyderabad",elig:"Bachelor's degree",desc:"Detailed role and software engineering team information.",resp:["Build tools"],expType:"fresher"}
});
test("Exact employer job page with Apply outranks ambiguous Workday shell",()=>{
 const exact=candidate(1,"Exact Lever page opened today with job-specific Apply link");
 const shell=candidate(2,"Official Workday result was indexed last week, exact page rendered as a blank shell");
 assert.ok(evidenceScore(exact)>evidenceScore(shell)+100);
});
test("Move source-supported backup listings ahead of uncertain priority without marking them expired",()=>{
 const priority=Array.from({length:10},(_,i)=>candidate(i,"Workday page rendered as a blank shell"));
 const backup=Array.from({length:10},(_,i)=>candidate(i+10,"Exact job page opened today with job-specific Apply link"));
 const batch={batchId:"2026-10-13",status:"reviewing",priority,backup};
 const result=reprioritizeBeforeReview(batch);
 assert.equal(result.changed,true);
 assert.deepEqual(result.batch.priority.map(x=>x.id),backup.map(x=>x.id));
 assert.equal(result.batch.priority[0].reviewedStatus,"unreviewed");
 assert.equal(batch.priority[0].id,"0");
});
test("Never reorder once any manual Live, Expired or Unsure decision is made",()=>{
 const priority=Array.from({length:10},(_,i)=>candidate(i,"Blank Workday shell"));
 const backup=Array.from({length:10},(_,i)=>candidate(i+10,"Exact job page with Apply"));
 priority[0].reviewedStatus="expired";
 const result=reprioritizeBeforeReview({priority,backup});
 assert.equal(result.changed,false);
});
test("Reject duplicate employers or incomplete batch without altering data",()=>{
 const priority=Array.from({length:10},(_,i)=>candidate(i,"Exact page"));
 const backup=Array.from({length:10},(_,i)=>candidate(i+10,"Exact page"));
 backup[0].company=priority[0].company;
 assert.equal(reprioritizeBeforeReview({priority,backup}).changed,false);
 assert.equal(reprioritizeBeforeReview({priority,backup:[]}).changed,false);
});
