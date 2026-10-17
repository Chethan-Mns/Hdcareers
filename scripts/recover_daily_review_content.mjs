import fs from "node:fs";
import {extractOfficialJob} from "../api/admin/extract-job.js";
import {enrichReviewedCandidate} from "../lib/review-enrichment.js";
import {employerKey} from "../lib/review-rules.js";

const path=process.argv[2]||"data/daily-review-batch.json";
const write=process.argv.includes("--apply");
const original=fs.readFileSync(path,"utf8");
const data=JSON.parse(original);
if(!["reviewing","waiting"].includes(data.status))process.exit(0);
const all=[...(data.priority||[]),...(data.backup||[])];
let recovered=0,held=0;
for(const candidate of all){
 const job=candidate.job;
 if(!job||!candidate.apply?.startsWith("https://")||job.apply!==candidate.apply){
  held++;continue;
 }
 const missing=["elig","desc","loc","sourceName"].some(k=>!String(job[k]||"").trim())||
   !Array.isArray(job.resp)||!job.resp.some(x=>String(x||"").trim());
 if(!missing)continue;
 try{
  const extracted=await extractOfficialJob(candidate.apply);
  // Reuse the strict enrichment identity, requisition, exact URL, and source-evidence gates.
  // Discovery enrichment does not imply owner approval or an active listing.
  const temporary={...candidate,reviewedStatus:"live",reviewedAt:candidate.reviewedAt||new Date().toISOString()};
  const result=enrichReviewedCandidate(temporary,extracted);
  if(!result.recovered.length){held++;continue;}
  candidate.job={...result.candidate.job,status:job.status};
  candidate.sourceEnrichment=result.candidate.sourceEnrichment;
  recovered++;
 }catch(e){
  held++;
  console.log("HOLD",candidate.company,":",String(e.message||e).slice(0,180));
 }
}
const updated=JSON.stringify(data,null,2)+"\n";
if(write&&updated!==original){
 fs.writeFileSync(path,updated);
}
console.log(JSON.stringify({attempted:all.length,recovered,held,write},null,2));
