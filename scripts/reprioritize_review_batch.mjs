import fs from "node:fs";
import {reprioritizeBeforeReview} from "../lib/review-ranking.js";
const path=process.argv[2]||"data/daily-review-batch.json";
const original=JSON.parse(fs.readFileSync(path,"utf8"));
const result=reprioritizeBeforeReview(original);
console.log(result.reason);
if(result.changed&&process.argv.includes("--apply")) {
 fs.writeFileSync(path,JSON.stringify(result.batch,null,2)+"\n");
 console.log("Reordered 10 Priority and 10 Backup candidates without changing any decisions.");
}
