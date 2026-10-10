import test from "node:test";
import assert from "node:assert/strict";
import {createAdminSession} from "../lib/admin-auth.js";
import handler from "../api/admin/reel-kit.js";

process.env.ADMIN_USERNAME="owner";
process.env.ADMIN_PASSWORD="test-owner";
process.env.ADMIN_SESSION_SECRET="test-session-secret-long-enough";
process.env.GITHUB_PUBLISH_TOKEN="test-github-token";
process.env.ADMIN_GITHUB_REPO="Chethan-Mns/Hdcareers";
process.env.ADMIN_GITHUB_BASE="main";
delete process.env.VERCEL_ENV;
const good={id:112,company:"Accenture",role:"AI/ML Computational Science Associate",loc:"Bengaluru",page:"jobs/accenture-ai-ml-computational-science-associate-bengaluru-aioc-s01665344.html",apply:"https://www.accenture.com/job/112",status:"active",verifiedDate:"10 Oct 2026",expType:"fresher",expYears:"0–1 year",elig:"BE or BTech"};
const expired={...good,id:900,company:"Expired company",status:"expired"};
let selection={jobId:null,status:"not_selected",selectedAt:null,postedAt:null};
const commits=[];
const originalFetch=globalThis.fetch;
globalThis.fetch=async(url,options={})=>{
  const path=String(url);const method=options.method||"GET";
  let result={};
  if(method==="GET"&&path.includes("/contents/data/jobs.json"))result={content:Buffer.from(JSON.stringify([good,expired])).toString("base64"),sha:"jobs-sha"};
  else if(method==="GET"&&path.includes("/contents/data/reel-selection.json"))result={content:Buffer.from(JSON.stringify(selection)).toString("base64"),sha:"selection-sha"};
  else if(method==="PUT"&&path.includes("/contents/data/reel-selection.json")){
    const body=JSON.parse(options.body);assert.equal(body.branch,"main");
    assert.equal(body.sha,"selection-sha");
    selection=JSON.parse(Buffer.from(body.content,"base64").toString("utf8"));commits.push(body.message);
    result={commit:{sha:"test-"+commits.length}};
  }else throw Error("Unexpected GitHub mock "+path+" "+method);
  return {ok:true,status:200,text:async()=>JSON.stringify(result)};
};
const token=createAdminSession();
const req=(method,body,origin)=>({method,body,headers:{host:"hdcareers.in",cookie:"hd_admin_session="+token,...(origin?{origin}:{})}});
const res=()=>({statusCode:200,headers:{},setHeader(k,v){this.headers[k]=v;return this},status(n){this.statusCode=n;return this},json(v){this.body=v;return this}});
async function call(method,body,origin){const response=res();await handler(req(method,body,origin),response);return response}
test("GET only serves verified active published jobs",async()=>{
 const a=await call("GET");assert.equal(a.statusCode,200);assert.deepEqual(a.body.jobs.map(j=>j.id),[112]);assert.equal(a.body.selection.status,"not_selected");
});
test("Admin can manually select, mark posted, undo and clear a reel",async()=>{
 let a=await call("POST",{action:"select",jobId:112});assert.equal(a.statusCode,200);assert.equal(a.body.selection.jobId,112);assert.equal(a.body.selection.status,"selected");
 a=await call("GET");assert.equal(a.body.selection.job.company,"Accenture");
 a=await call("POST",{action:"mark_posted"});assert.equal(a.statusCode,200);assert.equal(a.body.selection.status,"posted");
 a=await call("POST",{action:"mark_unposted"});assert.equal(a.statusCode,200);assert.equal(a.body.selection.status,"selected");
 a=await call("POST",{action:"clear"});assert.equal(a.statusCode,200);assert.equal(a.body.selection.status,"not_selected");assert.equal(selection.jobId,null);assert.equal(commits.length,4);
});
test("Cannot select expired jobs, unknown ids or unsupported actions",async()=>{
 for(const body of [{action:"select",jobId:900},{action:"select",jobId:-1},{action:"select",jobId:1},{action:"hack",jobId:112}]){
 const a=await call("POST",body);assert.equal([400,409].includes(a.statusCode),true);assert.equal(commits.length,4);
 }
});
test("Cross-origin, unauthenticated and Preview POST are blocked before GitHub writes",async()=>{
 let a=await call("POST",{action:"select",jobId:112},"https://evil.example");assert.equal(a.statusCode,403);
 const noAuth=res();await handler({method:"POST",headers:{host:"hdcareers.in"},body:{action:"select",jobId:112}},noAuth);assert.equal(noAuth.statusCode,401);
 process.env.VERCEL_ENV="preview";a=await call("POST",{action:"select",jobId:112});assert.equal(a.statusCode,403);
 delete process.env.VERCEL_ENV;assert.equal(commits.length,4);
});
test.after(()=>{globalThis.fetch=originalFetch});
