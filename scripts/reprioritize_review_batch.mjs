import fs from "node:fs";
import {reprioritizeBeforeReview} from "../lib/review-ranking.js";

const file=process.argv[2]||"data/daily-review-batch.json";
const safeLoad=(path,fallback)=>{
 try{return JSON.parse(fs.readFileSync(path,"utf8"));}
 catch(e){if(e.code==="ENOENT")return fallback;throw e;}
};
const batch=safeLoad(file,null);
const publishedJobs=safeLoad("data/jobs.json",[]);
const deliveries=safeLoad("data/telegram-deliveries.json",{});
const result=reprioritizeBeforeReview(batch,{publishedJobs,deliveries});
console.log(result.reason);
if(result.changed&&process.argv.includes("--apply")){
 fs.writeFileSync(file,JSON.stringify(result.batch,null,2)+"\n");
 console.log("Selected fresher-first 8/1/1 shortlist, excluded published duplicates, and preserved manual review status.");
 if(result.batch.ranking?.shortfalls){
  console.log("Category shortfalls (new discovery required):",JSON.stringify(result.batch.ranking.shortfalls));
 }
}
