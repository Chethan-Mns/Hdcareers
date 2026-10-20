import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import pushHandler from "../lib/admin-push-handler.js";
const read=path=>fs.readFileSync(new URL("../"+path,import.meta.url),"utf8");
function fakeRes(){return {statusCode:200,body:null,headers:{},setHeader(k,v){this.headers[k]=v;return this},status(v){this.statusCode=v;return this},json(v){this.body=v;return this}}}
test("Unauthenticated callers cannot register devices or trigger test pushes",async()=>{
 for(const action of ["register","unregister","test"]){
  const out=fakeRes();
  await pushHandler({method:"POST",headers:{},body:{action}},out);
  assert.equal(out.statusCode,401);
  assert.equal(out.body.error,"Authentication required.");
 }
});
test("Firebase push routes reuse session serverless function",()=>{
 const session=read("api/admin/session.js"),rewrite=JSON.parse(read("vercel.json"));
 assert.match(session,/android-devices/);
 assert.match(session,/pushHandler/);
 assert.ok(rewrite.rewrites.some(x=>x.source==="/api/admin/android-devices"&&x.destination.includes("adminOperation=android-devices")));
});
test("Client API key is supplied at build time, not hardcoded in source",()=>{
 const gradle=read("android-admin/app/build.gradle.kts");
 const workflow=read(".github/workflows/android-admin-build.yml");
 assert.match(gradle,/setting\("FIREBASE_API_KEY"\)/);
 assert.match(workflow,/vars.HD_FIREBASE_API_KEY/);
 assert.match(workflow,/vars.HD_FIREBASE_PROJECT_ID/);
 assert.match(workflow,/vars.HD_FIREBASE_APP_ID/);
 assert.match(workflow,/vars.HD_FIREBASE_SENDER_ID/);
 assert.doesNotMatch(gradle,/AIzaSy/);
});
test("Private signed releases require signing key and configured Firebase",()=>{
 const workflow=read(".github/workflows/android-admin-private-release.yml");
 for(const name of ["HD_ANDROID_KEYSTORE_BASE64","HD_ANDROID_KEYSTORE_PASSWORD","HD_ANDROID_KEY_ALIAS","HD_ANDROID_KEY_PASSWORD"])assert.ok(workflow.includes("secrets."+name));
 assert.match(workflow,/apksigner verify/);
 assert.match(workflow,/testReleaseUnitTest/);
});
test("Automated push requires dedicated secret and only new complete review batches",()=>{
 const workflow=read(".github/workflows/android-review-notify.yml");
 const server=read("lib/admin-push-handler.js");
 assert.match(workflow,/ANDROID_PUSH_DISPATCH_SECRET/);
 assert.match(workflow,/1<=len\(priority\)\+len\(backup\)<=20/);
 assert.match(workflow,/len\(set\(names\)\)!=len\(names\)/);
 assert.match(server,/safe\(req.headers\?\.\["x-hd-push-key"\],secret\)/);
});

test("Expiry alerts require trusted secret, are deduplicated by scan, and route to the correct Android tab",()=>{
 const push=read("lib/admin-push-handler.js");
 const workflow=read(".github/workflows/android-expiry-notify.yml");
 const client=read("android-admin/app/src/main/java/in/hdcareers/admin/Notifications.kt");
 const activity=read("android-admin/app/src/main/java/in/hdcareers/admin/MainActivity.kt");
 assert.match(push,/notify_expiry/);
 assert.match(push,/const once=scope\+kind\+"/);
 assert.match(push,/reviewCount<1/);
 assert.match(workflow,/notify_checker/);
 assert.doesNotMatch(workflow,/current_keys==previous_keys/);
 assert.match(workflow,/ANDROID_PUSH_DISPATCH_SECRET/);
 assert.match(workflow,/data\/availability-status\.json/);
 assert.match(client,/hd_expiry_updates/);
 assert.match(client,/putExtra\("open_expiry",openExpiry\)/);
 assert.match(activity,/open_expiry/);
});
test("Production Android requests hourly Telegram and distinguishes accepted from delivered",()=>{
 const native=read("android-admin/app/src/main/java/in/hdcareers/admin/AdminApi.kt");
 const backend=read("api/admin/publish.js");
 const kotlin=read("android-admin/app/src/main/java/in/hdcareers/admin/PremiumScreens.kt");
 assert.match(native,/put\("telegramDeliveryMode","hourly"\)/);
 assert.match(backend,/telegramHourlyPending/);
 assert.match(backend,/const queued=queueItems\.find/);
 assert.match(kotlin,/Confirm & Start/);
 assert.match(kotlin,/ProAnalyticsV2/);
});

test("Expiry review lists all statuses lazily, stages clicks locally and preserves Home exceptions",()=>{
 const checker=read("android-admin/app/src/main/java/in/hdcareers/admin/PremiumMore.kt");
 const home=read("android-admin/app/src/main/java/in/hdcareers/admin/PremiumScreens.kt");
 const model=read("android-admin/app/src/main/java/in/hdcareers/admin/AdminViewModel.kt");
 assert.match(checker,/\.filter \{ it\.optString\("state"\) in listOf\("active","expired","review"\) \}/);
 assert.match(checker,/rememberLazyListState/);
 assert.match(checker,/scrollToItem\(0\)/);
 assert.match(checker,/itemsIndexed\(visibleReviews/);
 assert.match(checker,/vm\.stageExpiryReview\(jobId,"keep"\)/);
 assert.match(checker,/vm(?:::|\.)publishExpiryDraft/);
 assert.match(checker,/confirmation=jobId to "expire"/);
 assert.match(home,/pendingExpiryReviews/);
 assert.match(home,/Review "\+pending\.size\+" pending jobs/);
 assert.match(model,/fun refreshOperationsQuietly/);
 assert.match(model,/fun publishExpiryDraft/);
 assert.match(model,/api\.resolveCheckerBatch\(submission\)/);
});
test("Checker and publishing transitions trigger independently deduplicated FCM notifications",()=>{
 const push=read("lib/admin-push-handler.js");
 const checker=read(".github/workflows/android-expiry-notify.yml");
 const publishing=read(".github/workflows/admin-job-generator.yml");
 const hourly=read(".github/workflows/hourly-telegram-queue.yml");
 assert.match(push,/notify_checker/);
 assert.match(push,/notify_publishing/);
 assert.match(push,/notify_telegram/);
 assert.match(push,/crypto\.createHash\("sha256"\)\.update\(batchId\)/);
 assert.match(checker,/notify_checker/);
 assert.match(publishing,/notify_publishing/);
 assert.match(hourly,/steps\.claim\.outputs\.claimed == 'true'/);
 assert.match(hourly,/notify_telegram/);
 assert.match(read("android-admin/app/src/main/java/in/hdcareers/admin/Notifications.kt"),/message\.data\["kind"\]=="checker"/);
});
