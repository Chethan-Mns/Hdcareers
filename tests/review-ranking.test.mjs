import test from "node:test";
import assert from "node:assert/strict";
import {evidenceScore,reprioritizeBeforeReview} from "../lib/review-ranking.js";
const candidate=(i,reason,reviewedStatus="unreviewed")=>({
 id:String(i),company:"Employer "+i,role:"Software Engineer",cat:"it",
 verificationReason:reason,verificationVerdict:"live",reviewedStatus,
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
 assert.deepEqual(result.batch.priority.map(x=>x.id),backup.slice(0,8).map(x=>x.id));
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

const ready=(i,cat="it",expType="fresher",name="Employer "+i)=>({
 id:String(i),company:name,role:cat==="internship"?"Software Engineering Intern":"Software Engineer "+i,
 verificationReason:"Exact official posting with active application form",verificationVerdict:"live",
 reviewedStatus:"unreviewed",
 job:{company:name,cat,expType,jobId:String(i),role:cat==="internship"?"Software Engineering Intern":"Software Engineer "+i,
  apply:"https://jobs.example.org/"+i,loc:"Bengaluru",elig:"Official degree requirements",
  desc:"Official full job description for this company and engineering opportunity.",resp:["Build software"]}
});
test("Prefer exactly eight verified-fresher IT, one non-IT and one internship when available",()=>{
 const pool=[
  ...Array.from({length:8},(_,i)=>ready(i,"it","fresher")),
  ready(8,"nonit","fresher"),
  ready(9,"internship","fresher"),
  ...Array.from({length:10},(_,i)=>ready(i+10,"it","experienced"))
 ];
 const batch={priority:pool.slice(10),backup:pool.slice(0,10)};
 const out=reprioritizeBeforeReview(batch);
 assert.equal(out.changed,true);
 assert.deepEqual(out.batch.ranking.selected,{fresherIT:8,nonIT:1,training:1});
 assert.deepEqual(out.batch.ranking.shortfalls,{fresherIT:0,nonIT:0,training:0});
 assert.equal(out.batch.priority.length,10);
 assert.deepEqual(new Set(out.batch.priority.map(x=>x.company)).size,10);
});
test("Never recycle a job already in website history, even with a fresh shortlist entry",()=>{
 const all=Array.from({length:20},(_,i)=>ready(i));
 const original={priority:all.slice(0,10),backup:all.slice(10)};
 const published=[{company:all[0].company,role:all[0].role,jobId:"0",apply:all[0].job.apply,page:"jobs/old.html"}];
 const out=reprioritizeBeforeReview(original,{publishedJobs:published});
 assert.equal(out.changed,true);
 assert.ok(![...out.batch.priority,...out.batch.backup].some(c=>c.id==="0"));
 assert.equal(out.batch.ranking.excludedPreviouslyPublished.length,1);
 assert.equal(out.batch.priority.length,8);
 assert.equal(out.batch.backup.length,10);
});
test("Favor owner-priority employers when source evidence and eligibility are equal",()=>{
 const all=Array.from({length:20},(_,i)=>ready(i,"it","fresher"));
 all[19]=ready(19,"it","fresher","Microsoft");
 const out=reprioritizeBeforeReview({priority:all.slice(0,10),backup:all.slice(10)});
 assert.ok(out.batch.priority.some(x=>x.company==="Microsoft"));
});
test("Recently delivered company is deprioritized when fresh employer alternatives exist",()=>{
 const all=Array.from({length:20},(_,i)=>ready(i,"it","fresher"));
 all[0]=ready(0,"it","fresher","EY");
 all[19]=ready(19,"it","fresher","Microsoft");
 const now=new Date("2026-10-17T06:00:00Z");
 const result=reprioritizeBeforeReview({priority:all.slice(0,10),backup:all.slice(10)},{
  now,
  publishedJobs:[{page:"jobs/recent.html",company:"EY",role:"Other recent EY role",jobId:"different",apply:"https://example.org/old"}],
  deliveries:{"@HD_Careers|jobs/recent.html":{status:"delivered",page:"jobs/recent.html",deliveredAt:"2026-10-16T05:00:00Z"}}
 });
 assert.ok(!result.batch.priority.some(x=>x.company==="EY"));
 assert.ok(result.batch.priority.some(x=>x.company==="Microsoft"));
});
test("Never falsely classify experienced roles as fresher and report unfillable quotas",()=>{
 const all=[
  ...Array.from({length:3},(_,i)=>ready(i,"it","fresher")),
  ...Array.from({length:2},(_,i)=>ready(i+3,"internship","fresher")),
  ...Array.from({length:15},(_,i)=>ready(i+5,"it","experienced"))
 ];
 const out=reprioritizeBeforeReview({priority:all.slice(10),backup:all.slice(0,10)});
 assert.equal(out.batch.ranking.selected.fresherIT,3);
 assert.equal(out.batch.ranking.selected.nonIT,0);
 assert.equal(out.batch.ranking.shortfalls.fresherIT,5);
 assert.equal(out.batch.ranking.shortfalls.nonIT,1);
});

test("No substitution of experienced candidates for missing fresher IT or non-IT quota",()=>{
 const pool=[
  ...Array.from({length:3},(_,i)=>ready(i,"it","fresher")),
  ready(3,"internship","fresher"),
  ...Array.from({length:16},(_,i)=>ready(i+4,"it","experienced"))
 ];
 const out=reprioritizeBeforeReview({priority:pool.slice(0,10),backup:pool.slice(10)});
 assert.equal(out.batch.priority.length,4);
 assert.deepEqual(out.batch.ranking.selected,{fresherIT:3,nonIT:0,training:1});
 assert.deepEqual(out.batch.ranking.shortfalls,{fresherIT:5,nonIT:1,training:0});
 assert.equal(out.batch.priority.filter(j=>j.job.expType==="experienced").length,0);
});
test("Unconfirmed applicants must remain in backup and cannot be counted as Live",()=>{
 const all=[...Array.from({length:8},(_,i)=>ready(i)),ready(8,"nonit"),ready(9,"internship"),
  ...Array.from({length:10},(_,i)=>ready(i+10,"it","experienced"))];
 all[0].verificationVerdict="unconfirmed";
 const out=reprioritizeBeforeReview({priority:all.slice(0,10),backup:all.slice(10)});
 assert.equal(out.batch.ranking.selected.fresherIT,7);
 assert.equal(out.batch.ranking.shortfalls.fresherIT,1);
 assert.ok(!out.batch.priority.some(x=>x.id==="0"));
 assert.ok(out.batch.backup.some(x=>x.id==="0"));
});

test("Never rediscover exact employer job URL owner confirmed expired",()=>{
 const candidates=Array.from({length:20},(_,i)=>ready(i,"it","fresher"));
 const bad=candidates[1];
 const out=reprioritizeBeforeReview({priority:candidates.slice(0,10),backup:candidates.slice(10)},{
  ownerVerdicts:[{company:bad.company,officialUrl:bad.job.apply,manualVerdict:"expired"}]
 });
 assert.equal(out.changed,true);
 assert.ok(!out.batch.priority.concat(out.batch.backup).some(x=>x.id===bad.id));
 assert.equal(out.batch.ranking.excludedOwnerExpired.length,1);
});
test("Cisco generic homepage exception cannot be counted as source Live",()=>{
 const all=Array.from({length:20},(_,i)=>ready(i,"it","fresher"));
 all[19]=ready(19,"it","fresher","Cisco");
 all[19].verificationVerdict="unconfirmed";
 all[19].verificationReason="Exact requisition route redirects to generic careers homepage";
 const out=reprioritizeBeforeReview({priority:all.slice(0,10),backup:all.slice(10)});
 assert.ok(!out.batch.priority.some(x=>x.company==="Cisco"));
});
test("Owner-priority Dell and CGI outrank equally verified small employers",()=>{
 const all=Array.from({length:20},(_,i)=>ready(i,"it","fresher"));
 all[18]=ready(18,"it","fresher","Dell Technologies");
 all[19]=ready(19,"it","fresher","CGI");
 const out=reprioritizeBeforeReview({priority:all.slice(0,10),backup:all.slice(10)});
 assert.ok(out.batch.priority.some(x=>x.company==="Dell Technologies"));
 assert.ok(out.batch.priority.some(x=>x.company==="CGI"));
});
