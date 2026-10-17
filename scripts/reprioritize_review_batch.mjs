import fs from "node:fs";
import {reprioritizeBeforeReview} from "../lib/review-ranking.js";

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
const result=reprioritizeBeforeReview(batch,{publishedJobs,deliveries,ownerVerdicts,watchlist});
console.log(result.reason);
if(result.changed&&process.argv.includes("--apply")){
 fs.writeFileSync(file,JSON.stringify(result.batch,null,2)+"\n");
 console.log("Selected fresher-first 8/1/1 shortlist, excluded published duplicates, and preserved manual review status.");
 if(result.batch.ranking?.shortfalls){
  console.log("Category shortfalls (new discovery required):",JSON.stringify(result.batch.ranking.shortfalls));
 }
}
