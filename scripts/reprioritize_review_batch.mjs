import fs from "node:fs";
import {reprioritizeBeforeReview} from "../lib/review-ranking.js";
import {filterDiscoveryDuplicates} from "../lib/review-dedup.js";

const file=process.argv[2]||"data/daily-review-batch.json";
const safeLoad=(path,fallback)=>{
 try{return JSON.parse(fs.readFileSync(path,"utf8"));}
 catch(e){if(e.code==="ENOENT")return fallback;throw e;}
};
const batch=safeLoad(file,null);
if(String(batch?.batchId||"").includes("owner-requested-new-20")||String(batch?.batchId||"").startsWith("hd-android-two-job-test-")){
 console.log("Owner-approved review/test shortlist: preserve prepared candidates without auto-reordering or truncation.");
 process.exit(0);
}
const publishedJobs=safeLoad("data/jobs.json",[]);
const deliveries=safeLoad("data/telegram-deliveries.json",{});
const evidence=safeLoad("data/verification-benchmark-2026-10-17.json",{items:[]});
const ownerVerdicts=Array.isArray(evidence.items)?evidence.items:[];
const watchlist=safeLoad("data/employer-watchlist-87.json",null);
const archiveDir="data/review-batch-archive";
const archivedBatches=fs.existsSync(archiveDir)?fs.readdirSync(archiveDir)
 .filter(n=>n.endsWith(".json")).map(n=>safeLoad(archiveDir+"/"+n,null)).filter(Boolean):[];
// This runs even when discovery found just 1-14 jobs. Ranking quotas must never gate deduplication.
const scrub=filterDiscoveryDuplicates(batch,{publishedJobs,deliveries,archivedBatches,ownerVerdicts});
console.log(scrub.reason);
if(scrub.changed&&process.argv.includes("--apply")){
 fs.writeFileSync(file,JSON.stringify(scrub.batch,null,2)+"\n");
 console.log("Pre-review duplicate check removed "+scrub.removed.length+" jobs; "+scrub.batch.discoveryAudit.remaining+"/20 unique jobs remain.");
}
const result=reprioritizeBeforeReview(scrub.batch,{publishedJobs,deliveries,ownerVerdicts,watchlist});
console.log(result.reason);
if(scrub.batch?.discoveryAudit?.needsFreshDiscovery)
 console.log("DISCOVERY SHORTFALL (do not pad): "+JSON.stringify({priority:scrub.batch.discoveryAudit.priority,backup:scrub.batch.discoveryAudit.backup}));
if(result.changed&&process.argv.includes("--apply")){
 fs.writeFileSync(file,JSON.stringify(result.batch,null,2)+"\n");

 const held=result.batch.ranking?.needsSourceVerification||[];
 if(held.length){
  const sidecar="data/daily-review-source-recheck.json";
  const prior=safeLoad(sidecar,{items:[]});
  const byUrl=new Map((prior.items||[]).filter(x=>x.officialUrl).map(x=>[x.officialUrl,x]));
  for(const item of held){
   if(!item.officialUrl)continue;
   byUrl.set(item.officialUrl,{...item,batchId:batch.batchId,
      state:"needs_official_verification",lastSeen:batch.generatedAt||new Date().toISOString()});
  }
  fs.writeFileSync(sidecar,JSON.stringify({policy:"Keep inconclusive official jobs for rechecking. Never present as Live or automatically expire.",items:[...byUrl.values()]},null,2)+"\n");
  console.log("Deferred "+held.length+" source-uncertain jobs to "+sidecar+" without losing exact URLs.");
 }

 console.log("Selected two 6 technical / 2 non-IT / 2 internship shortlists, excluded published duplicates, and preserved manual review status.");
 if(result.batch.ranking?.shortfalls){
  console.log("Category shortfalls (new discovery required):",JSON.stringify(result.batch.ranking.shortfalls));
 }
}
