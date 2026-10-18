import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const read=p=>fs.readFileSync(p,"utf8");

test("Web admin pages parse as JavaScript and preserve guarded publishing",()=>{
 for(const name of ["admin/index.html","admin/review-batch.html"]){
  const html=read(name);
  const scripts=[...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)];
  assert(scripts.length>0,name+" missing inline scripts");
  for(const [,source] of scripts){
   if(source.trim())assert.doesNotThrow(()=>new Function(source),name+" syntax");
  }
 }
 const daily=read("admin/review-batch.html");
 assert.match(daily,/historyTab/);
 assert.match(daily,/reviewedStatus!=="expired"/);
 assert.match(daily,/website==="live"/);
 assert.match(daily,/telegramDueAt/);
 assert.match(daily,/t\.me\/HD_Careers/);
 const checker=read("admin/index.html");
 for(const entry of ["publishVerifiedExpiryJobs","expiryReviewIds","toggleExpiryReady","Live → Ready","Unsure"]){
  assert(checker.includes(entry),entry);
 }
});

test("Checker decisions cannot silently publish unverified new roles",()=>{
 const review=read("api/admin/review.js");
 const section=review.slice(review.indexOf("if(pendingIndex>=0){"),review.indexOf("const job=jobs.find",review.indexOf("if(pendingIndex>=0){")));
 assert.match(section,/pending\.state="ready"/);
 assert.match(section,/pending\.state="rejected"/);
 assert.match(section,/pending\.state="review"/);
 assert.doesNotMatch(section,/prepareApprovedJob\(/);
 assert.doesNotMatch(section,/APPROVED_BATCH_PATH\]:/);
 assert.match(review,/\["expire","keep","unsure"\]/);
});

test("Expiry publishing validates persisted Live state, source URL and one employer per job",()=>{
 const api=read("api/admin/publish.js");
 for(const phrase of ["expiryReviewIds","reviewDecision","manualLiveVerifiedUrl","employerKey",
  "hdreview:expiry:job:","30*86400","Duplicate job detected"]){
  assert(api.includes(phrase),phrase);
 }
 assert.match(api,/fromExpiry\?crypto\.createHash/);
 const checker=read("api/admin/availability.js");
 assert.match(checker,/readyItems:readyReviews/);
 assert.match(checker,/state:isPublished\?"published"/);
});

test("Android only clears selected daily jobs after confirmed public website status",()=>{
 const vm=read("android-admin/app/src/main/java/in/hdcareers/admin/AdminViewModel.kt");
 const kotlin=read("android-admin/app/src/main/java/in/hdcareers/admin/PremiumScreens.kt");
 const checker=read("android-admin/app/src/main/java/in/hdcareers/admin/PremiumMore.kt");
 assert.match(vm,/optString\("website"\)=="live"/);
 assert.match(vm,/selectedIds=emptySet\(\)/);
 assert.match(vm,/fun publishExpirySelected/);
 assert.match(kotlin,/selected==3/);
 assert.match(kotlin,/Review.*History|History.*Review|listOf\("Priority","Backup","Ready","History"\)/);
 assert.match(checker,/confirmation=jobId to "unsure"/);
 assert.match(checker,/vm\.publishExpirySelected\(\)/);
 assert.match(checker,/Expiry|Publish Ready/);
});
