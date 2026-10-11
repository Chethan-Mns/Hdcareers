import test from "node:test";
import assert from "node:assert/strict";
import {employerKey,employerAudit,isFresherIT,publishable,selectCandidates,reviewCounts} from "../lib/review-rules.js";

function candidate(id,company,cat="it",expType="fresher"){
 const apply="https://careers.example.com/req-"+id;
 return {id,company,cat,apply,reviewedStatus:"live",reviewedAt:"2026-10-11T09:00:00Z",
 job:{company,role:"Software Engineer "+id,cat,expType,loc:"Hyderabad",elig:"Bachelor's degree",
 desc:"Source-verified description",resp:["Develop systems"],apply,sourceName:"Official employer careers",
 status:"active"}};
}
const make=(priority,backup=[])=>({batchId:"2026-10-11",status:"reviewing",priority,backup});
test("Employer aliases are normalized across the full 20 positions",()=>{
 assert.equal(employerKey("HCL Technologies Ltd"),employerKey("HCLTech"));
 assert.equal(employerKey("EY"),employerKey("Ernst & Young"));
 assert.equal(employerKey("TCS"),employerKey("Tata Consultancy Services"));
 assert.equal(employerKey("AWS"),employerKey("Amazon"));
 assert.equal(employerKey("Google Cloud"),employerKey("Google"));
 const all=Array.from({length:20},(_,i)=>candidate(String(i),"Distinct Employer "+i));
 assert.deepEqual(employerAudit(make(all.slice(0,10),all.slice(10))).duplicates,[]);
 all[19].company="HCL Technologies";all[0].company="HCLTech";
 const report=employerAudit(make(all.slice(0,10),all.slice(10)));
 assert.equal(report.unique,19);assert.equal(report.duplicates.length,1);
});
test("Any 1 through 10 reviewed complete jobs can be selected across either list",()=>{
 const a=candidate("p","Google"),b=candidate("b","Microsoft");
 const batch=make([a],[b]);
 assert.deepEqual(selectCandidates(batch,["b"]).map(x=>x.id),["b"]);
 assert.deepEqual(selectCandidates(batch,["b","p"]).map(x=>x.id),["b","p"]);
 assert.throws(()=>selectCandidates(batch,[]),/1 to 10/);
 assert.throws(()=>selectCandidates(batch,["b","b"]),/different reviewed/);
 assert.throws(()=>selectCandidates(batch,["unknown"]),/no longer/);
});
test("Exactly 1, 5, 9 and 10 Live jobs can be published across lists",()=>{
 const all=Array.from({length:20},(_,i)=>candidate(String(i),"Employer "+i));
 const batch=make(all.slice(0,10),all.slice(10));
 for(const size of [1,5,9,10]){
  const ids=Array.from({length:size},(_,i)=>String((i%2===0)?i:i+10));
  assert.equal(selectCandidates(batch,ids).length,size);
 }
 assert.throws(()=>selectCandidates(batch,all.slice(0,11).map(c=>c.id)),/1 to 10/);
});
test("One employer per selection, even when presented under alias",()=>{
 const a=candidate("p","EY"),b=candidate("b","Ernst and Young");
 assert.throws(()=>selectCandidates(make([a],[b]),["p","b"]),/one job per employer/);
});
test("Expired, unsure, unreviewed or incomplete records must never publish",()=>{
 const a=candidate("a","Google");
 for(const status of ["expired","unsure","unreviewed"]){
  a.reviewedStatus=status;
  assert.equal(publishable(a),false);
  assert.throws(()=>selectCandidates(make([a]),["a"]),/Live/);
 }
 a.reviewedStatus="live";delete a.job.desc;
 assert.equal(publishable(a),false);
});
test("80 percent preference is based on verified fresher IT category",()=>{
 assert.equal(isFresherIT(candidate("f","Google")),true);
 assert.equal(isFresherIT(candidate("n","EY","nonit")),false);
 assert.equal(isFresherIT(candidate("e","Amazon","it","experienced")),false);
});
test("Counters separate reviewed readiness, incompleteness and expiry",()=>{
 const a=candidate("p","Google"),b=candidate("b","Microsoft");
 b.job.status="expired";b.reviewedStatus="expired";
 const x=candidate("x","Wipro");x.job.desc="";
 const m=reviewCounts(make([a,x],[b]),["p"]);
 assert.equal(m.selected,1);assert.equal(m.ready,1);assert.equal(m.incomplete,1);assert.equal(m.expired,1);
});
