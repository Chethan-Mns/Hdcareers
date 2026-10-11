import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createAdminSession} from "../lib/admin-auth.js";
import {createFakeRedis} from "./helpers/fake-redis.mjs";
import handler from "../api/admin/daily-batch.js";

process.env.ADMIN_USERNAME="owner";
process.env.ADMIN_PASSWORD="test-owner-password";
process.env.ADMIN_SESSION_SECRET="shadow-test-secret-not-production";
const redis=createFakeRedis();
process.env.HD_ADMIN_REDIS_URL=redis.url;
process.env.HD_ADMIN_REDIS_TOKEN="test-only-redis-token";
process.env.GITHUB_PUBLISH_TOKEN="shadow-github-mock";
process.env.ADMIN_GITHUB_BASE="main";

const liveJob={company:"Official Company",role:"Associate Developer",loc:"Bengaluru",elig:"BE/BTech",
 desc:"A correctly sourced employer description",resp:["Build actual products"],apply:"https://example.com/jobs/role-1",sourceName:"Official Company Careers",status:"review"};
const original=globalThis.fetch;
let edits=0,dispatches=0;
let state={batchId:"2026-10-11-0900-ist",generatedAt:"2026-10-11T03:30:00Z",status:"reviewing",priority:[
 {id:"source-job-1",company:"Official Company",role:"Associate Developer",cat:"it",reviewedStatus:"unreviewed",
 verificationReason:"Checked exact employer apply URL",job:liveJob}],backup:[],updatedAt:"2026-10-11T03:33:00Z"};
globalThis.fetch=async(url,options={})=>{
  const storeReply=redis.response(url,options);
  if(storeReply)return storeReply;
 const method=options.method||"GET";
 const path=String(url);
 if(path.includes("/dispatches")){dispatches++;throw Error("Review staging must never publish");}
 let body;
 if(method==="PUT"){
  body=JSON.parse(options.body);
  state=JSON.parse(Buffer.from(body.content,"base64").toString());
  edits++;
  return {ok:true,status:200,text:async()=>JSON.stringify({commit:{sha:"mock-update"}})};
 }
 if(method==="GET"&&path.includes("daily-review-batch.json")){
  return {ok:true,status:200,text:async()=>JSON.stringify({sha:"mock-blob",content:Buffer.from(JSON.stringify(state)).toString("base64")})};
 }
 throw Error("Unexpected API request: "+path+" "+method);
};
const session=await createAdminSession({username:"owner",role:"owner"});
function request(method,body,customHeaders={}){return {method,body,headers:{host:"hdcareers.in",cookie:"hd_admin_session="+session,...customHeaders}}}
function response(){return {statusCode:200,headers:{},setHeader(k,v){this.headers[k]=v;return this},status(s){this.statusCode=s;return this},json(data){this.data=data;return this}}}
async function call(method,body,headers){const res=response();await handler(request(method,body,headers),res);return res}

test("9 AM batch appears in Review Center API without publishing",async()=>{
 const r=await call("GET");assert.equal(r.statusCode,200);assert.equal(r.data.batchId,"2026-10-11-0900-ist");
 assert.equal(r.data.priority.length,1);assert.equal(dispatches,0);
});
test("Owner review decision saves to same GitHub JSON, never publishes",async()=>{
 const r=await call("POST",{action:"review",batchId:"2026-10-11-0900-ist",candidateId:"source-job-1",decision:"live"});
 assert.equal(r.statusCode,200);assert.equal(r.data.priority[0].reviewedStatus,"live");assert.equal(r.data.priority[0].job.status,"active");
 assert.equal(edits,1);assert.equal(dispatches,0);
});
test("Cannot submit insufficient priority jobs despite source LIVE review",async()=>{
 const r=await call("POST",{action:"submitted",batchId:"2026-10-11-0900-ist"});
 assert.equal(r.statusCode,400);assert.match(r.data.error,/Choose 1 to 10/i);assert.equal(edits,1);
});
test("Stale batch, disallowed origin and preview writes are blocked",async()=>{
 let r=await call("POST",{action:"review",batchId:"stale",candidateId:"source-job-1",decision:"expired"});
 assert.equal(r.statusCode,409);
 r=await call("POST",{action:"review",batchId:"2026-10-11-0900-ist",candidateId:"source-job-1",decision:"expired"},{origin:"https://attacker.example"});
 assert.equal(r.statusCode,403);
 process.env.VERCEL_ENV="preview";
 r=await call("POST",{action:"review",batchId:"2026-10-11-0900-ist",candidateId:"source-job-1",decision:"expired"});
 assert.equal(r.statusCode,403);delete process.env.VERCEL_ENV;
 assert.equal(edits,1);
});
test("Reject unauthenticated review attempts",async()=>{
 const req={method:"POST",headers:{host:"hdcareers.in"},body:{action:"review",batchId:"2026-10-11-0900-ist",candidateId:"source-job-1",decision:"expired"}};
 const res=response();await handler(req,res);
 assert.equal(res.statusCode,401);assert.equal(edits,1);
});
test("Admin Review Center inline JS parses and displays verification evidence",()=>{
 const page=fs.readFileSync("admin/review-batch.html","utf8");
 const script=page.match(/<script>([\s\S]*?)<\/script>/);
 assert(script);
 assert.doesNotThrow(()=>new Function(script[1]));
 assert.match(script[1],/verificationReason/);
 assert.match(script[1],/batchInfo/);
 assert.match(script[1],/isComplete/);
});
test("Explicit human approval changes job status; expired and unsure undo it",async()=>{
 assert.equal(state.priority[0].job.status,"active");
 assert(state.priority[0].job.manualLiveVerifiedAt);
 const expired=await call("POST",{action:"review",batchId:"2026-10-11-0900-ist",candidateId:"source-job-1",decision:"expired"});
 assert.equal(expired.statusCode,200);
 assert.equal(expired.data.priority[0].reviewedStatus,"expired");
 assert.equal(expired.data.priority[0].job.status,"expired");
 assert.equal(expired.data.priority[0].job.manualLiveVerifiedAt,undefined);
 const unsure=await call("POST",{action:"review",batchId:"2026-10-11-0900-ist",candidateId:"source-job-1",decision:"unsure"});
 assert.equal(unsure.statusCode,200);
 assert.equal(unsure.data.priority[0].job.status,"review");
 assert.equal(unsure.data.priority[0].reviewedStatus,"unsure");
 assert.equal(dispatches,0);
 assert.equal(edits,3);
});
test("One selected Live job can be submitted and records exact ID",async()=>{
 let r=await call("POST",{action:"review",batchId:"2026-10-11-0900-ist",candidateId:"source-job-1",decision:"live"});
 assert.equal(r.statusCode,200);
 r=await call("POST",{action:"submitted",batchId:"2026-10-11-0900-ist",candidateIds:["source-job-1"],requestId:"test-subset"});
 assert.equal(r.statusCode,200);
 assert.equal(r.data.status,"submitted");
 assert.deepEqual(r.data.publication.candidateIds,["source-job-1"]);
 assert.equal(dispatches,0);
});
test.after(()=>{globalThis.fetch=original});
