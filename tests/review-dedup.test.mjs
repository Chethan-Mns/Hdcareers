import test from "node:test";
import assert from "node:assert/strict";
import {filterDiscoveryDuplicates,jobUrl} from "../lib/review-dedup.js";

const candidate=(id,company,role="Software Engineer",url="https://jobs.example.org/"+id,jobId=String(id))=>({
 id:String(id),company,role,reviewedStatus:"unreviewed",verificationVerdict:"live",
 job:{company,role,cat:"it",expType:"fresher",jobId,apply:url}
});
const batch=(priority,backup=[])=>({batchId:"2026-10-26-0900-ist",status:"reviewing",priority,backup});

test("URL identity drops tracking but preserves real requisition query parameters",()=>{
 assert.equal(jobUrl("https://Example.org/jobs/123/?utm_source=x&gh_src=link"),jobUrl("https://example.org/jobs/123"));
 assert.notEqual(jobUrl("https://example.org/jobs?jobId=123"),jobUrl("https://example.org/jobs?jobId=124"));
});
test("Pre-review exclusion works for an undersized 9-job shortlist",()=>{
 const a=Array.from({length:9},(_,i)=>candidate(i+1,"Employer "+i));
 a[0]=candidate("1","Sprinto","Renamed AI Intern","https://jobs.lever.co/sprinto/abc?utm_source=linkedin");
 const output=filterDiscoveryDuplicates(batch(a),{
   publishedJobs:[{company:"Sprinto",role:"AI Implementation Intern",apply:"https://jobs.lever.co/sprinto/abc"}]
 });
 assert.equal(output.batch.priority.length,8);
 assert.equal(output.batch.discoveryAudit.excludedCount,1);
 assert.equal(output.removed[0].reason,"already_published");
 assert.equal(output.batch.discoveryAudit.priority.shortfalls.fresherIT>=0,true);
});
test("Archived review requisitions, owner-expired links and employer aliases are excluded",()=>{
 const priority=[candidate(1,"Deloitte","Analyst","https://careers.example.com/a","123"),
   candidate(2,"EY","Associate","https://careers.example.com/b")];
 const backup=[candidate(3,"Deloitte USI","Other Analyst","https://careers.example.com/c","345"),
   candidate(4,"Microsoft","Software Engineer","https://careers.example.com/d")];
 const out=filterDiscoveryDuplicates(batch(priority,backup),{
   archivedBatches:[batch([candidate("x","Deloitte","Old role","https://other.example.com/changed-url","123")])],
   ownerVerdicts:[{company:"EY",officialUrl:"https://careers.example.com/b",manualVerdict:"expired"}]
 });
 assert.equal(out.batch.priority.length,0);
 assert.equal(out.batch.backup.length,2);
 assert.deepEqual(out.removed.map(x=>x.reason),["previously_reviewed_official_requisition","owner_confirmed_expired"]);
});
test("One company only across both lists, including aliases",()=>{
 const out=filterDiscoveryDuplicates(batch([candidate(1,"EY")],[candidate(2,"Ernst & Young","Operations Associate")]));
 assert.equal(out.batch.priority.length,1);
 assert.equal(out.batch.backup.length,0);
 assert.equal(out.removed[0].reason,"repeated_employer_across_priority_and_backup");
});
test("Manual review and published historical batches are immutable",()=>{
 const live=candidate(1,"Amazon");live.reviewedStatus="live";live.reviewedAt="2026-10-25T10:00:00Z";
 const b=batch([live,candidate(2,"Amazon")]);
 assert.equal(filterDiscoveryDuplicates(b).changed,false);
 assert.equal(filterDiscoveryDuplicates({...b,status:"published"}).changed,false);
});
test("Unfilled shortlist has a transparent audit and is idempotent",()=>{
 const first=filterDiscoveryDuplicates(batch([candidate(1,"Amazon")]));
 assert.equal(first.changed,true);
 assert.equal(first.batch.discoveryAudit.remaining,1);
 assert.equal(first.batch.discoveryAudit.needsFreshDiscovery,true);
 const again=filterDiscoveryDuplicates(first.batch);
 assert.equal(again.changed,false);
 assert.equal(again.batch.priority.length,1);
});
test("All repeats can be removed, leaving zero honest candidates without fabricating",()=>{
 const a=candidate(1,"Amazon");
 const out=filterDiscoveryDuplicates(batch([a]),{publishedJobs:[a.job]});
 assert.equal(out.batch.priority.length,0);
 assert.equal(out.batch.discoveryAudit.remaining,0);
 assert.equal(out.batch.discoveryAudit.excludedCount,1);
});
