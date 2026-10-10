import test from "node:test";
import assert from "node:assert/strict";
import {verifyCredentials,createAdminSession,requireAdmin} from "../lib/admin-auth.js";
import {createEditor,getUser,lookupSession,issueSession,setEditorState,removeSession,audit,auditEntries} from "../lib/admin-store.js";
import teamHandler from "../api/admin/team.js";
import auditHandler from "../api/admin/audit.js";
import trafficHandler from "../api/admin/traffic.js";
import publishHandler from "../api/admin/publish.js";
import availabilityHandler from "../api/admin/availability.js";
import ownerPasswordHandler from "../api/admin/owner-password.js";
import {ownerPasswordOverride} from "../lib/admin-store.js";

process.env.ADMIN_USERNAME="owner";
process.env.ADMIN_PASSWORD="test-owner-placeholder";
process.env.ADMIN_SESSION_SECRET="test-signing-placeholder";
process.env.HD_ADMIN_REDIS_URL="https://example.test";
process.env.HD_ADMIN_REDIS_TOKEN="test-store-placeholder";
const store=new Map();
globalThis.fetch=async(_url,options)=>{
  const [op,k,...args]=JSON.parse(options.body);
  let value=null;
  if(op==="GET")value=store.get(k)??null;
  if(op==="SET"){if(!args.includes("NX")||!store.has(k)){store.set(k,args[0]);value="OK";}}
  if(op==="DEL")value=store.delete(k)?1:0;
  if(op==="INCR"){value=Number(store.get(k)||0)+1;store.set(k,String(value));}
  if(op==="SADD"){const list=store.get(k)||[];if(!list.includes(args[0]))list.push(args[0]);store.set(k,list);value=1;}
  if(op==="SMEMBERS")value=store.get(k)||[];
  if(op==="LPUSH"){const list=store.get(k)||[];list.unshift(args[0]);store.set(k,list);value=list.length;}
  if(op==="LRANGE")value=(store.get(k)||[]).slice(0,args[1]+1);
  if(op==="LTRIM"){const list=store.get(k)||[];store.set(k,list.slice(0,args[1]+1));value="OK";}
  if(op==="EXPIRE")value=1;
  return {ok:true,json:async()=>({result:value})};
};
const req=token=>({method:"GET",headers:{cookie:"hd_admin_session="+token,host:"hdcareers.in"}});
const res=()=>({statusCode:200,headers:{},setHeader(k,v){this.headers[k]=v;return this},status(n){this.statusCode=n;return this},json(v){this.body=v;return this}});

test("Owner credentials are unchanged and new Owner session is revocable",async()=>{
  const user=await verifyCredentials("owner","test-owner-placeholder");
  assert.equal(user.role,"owner");
  const token=await createAdminSession(user);
  assert.equal((await lookupSession(token)).role,"owner");
  await removeSession(token);
  assert.equal(await lookupSession(token),null);
});
test("Job Editor credentials are salted, distinct and role-restricted",async()=>{
  await createEditor("job.friend","ExampleStrongPassword-2026","owner");
  const record=await getUser("job.friend");
  assert.equal(record.role,"job_editor");
  assert.equal(JSON.stringify(record).includes("ExampleStrongPassword-2026"),false);
  assert.equal((await verifyCredentials("job.friend","ExampleStrongPassword-2026")).role,"job_editor");
  const token=await issueSession("job.friend","job_editor");
  const denied=res();
  assert.equal(await requireAdmin(req(token),denied,["owner"]),false);
  assert.equal(denied.statusCode,403);
  assert.equal(await requireAdmin(req(token),res(),["job_editor"]),true);
  await setEditorState("job.friend","disable");
  assert.equal(await lookupSession(token),null);
  await setEditorState("job.friend","enable");
  assert.equal(await lookupSession(token),null);
});
test("Owner-only audit entries store actors and actions",async()=>{
  await audit({username:"owner",role:"owner",action:"account.disable",target:"job.friend",result:"success"});
  const rows=await auditEntries(10);
  assert.equal(rows[0].username,"owner");
  assert.equal(rows[0].action,"account.disable");
});

test("Job Editor cannot access Owner team, audit or private analytics APIs",async()=>{
  await setEditorState("job.friend","enable");
  const token=await issueSession("job.friend","job_editor");
  for(const handler of [teamHandler,auditHandler,trafficHandler]){
    const response=res();
    await handler(req(token),response);
    assert.equal(response.statusCode,403);
  }
  const owner=await issueSession("owner","owner");
  const response=res();
  await teamHandler(req(owner),response);
  assert.equal(response.statusCode,200);
  assert.equal(response.body.editors[0].username,"job.friend");
});

test("Vercel preview cannot mutate production job data",async()=>{
  process.env.VERCEL_ENV="preview";
  try{
    const token=await issueSession("owner","owner");
    const response=res();
    await publishHandler({...req(token),method:"POST",body:{jobs:[]}},response);
    assert.equal(response.statusCode,403);
  }finally{
    delete process.env.VERCEL_ENV;
  }
});

test("Existing Owner usernames with email-style characters remain accepted",async()=>{
 const original=process.env.ADMIN_USERNAME;
 try{
  process.env.ADMIN_USERNAME="owner@example.com";
  const who=await verifyCredentials("OWNER@EXAMPLE.COM","test-owner-placeholder");
  assert.equal(who.username,"owner@example.com");
  assert.equal(who.role,"owner");
  const token=await createAdminSession(who);
  assert.equal((await lookupSession(token)).role,"owner");
 }finally{process.env.ADMIN_USERNAME=original}
});


test("Job Editor can see the checker endpoint, but Preview cannot trigger a GitHub write",async()=>{
 const editor=await issueSession("job.friend","job_editor");
 const owner=await issueSession("owner","owner");
 const prior=process.env.VERCEL_ENV;
 process.env.VERCEL_ENV="preview";
 try{
   for(const token of [editor,owner]){
     const response=res();
     await availabilityHandler({...req(token),method:"POST",body:{}},response);
     assert.equal(response.statusCode,403);
     assert.match(response.body.error,/Preview is read-only/i);
   }
 }finally{
   if(prior===undefined)delete process.env.VERCEL_ENV;
   else process.env.VERCEL_ENV=prior;
 }
});

test("Job Editor checker trigger is server-authorized, GitHub-backed and audited",async()=>{
 const previousFetch=globalThis.fetch;
 const previousEnv=process.env.VERCEL_ENV;
 const previousPublishToken=process.env.GITHUB_PUBLISH_TOKEN;
 const editor=await issueSession("job.friend","job_editor");
 process.env.VERCEL_ENV="production";
 process.env.GITHUB_PUBLISH_TOKEN="test-github-token";
 const githubCalls=[];
 globalThis.fetch=async(url,options={})=>{
   if(String(url).startsWith("https://api.github.com/repos/")){
     githubCalls.push({url:String(url),method:options.method||"GET"});
     let payload;
     if(String(url).includes("/actions/workflows/job-availability.yml/runs"))payload={workflow_runs:[]};
     else if(options.method==="PUT" && String(url).includes("/contents/data/availability-trigger.json"))payload={commit:{sha:"mock-commit"}};
     else if(String(url).includes("/contents/data/availability-trigger.json"))payload={sha:"mock-file",content:Buffer.from("{}").toString("base64")};
     else throw Error("Unexpected mocked GitHub URL: "+url);
     return {ok:true,text:async()=>JSON.stringify(payload)};
   }
   return previousFetch(url,options);
 };
 try{
   const response=res();
   await availabilityHandler({...req(editor),method:"POST",body:{}},response);
   assert.equal(response.statusCode,202);
   assert.equal(response.body.queued,true);
   assert.equal(response.body.commitSha,"mock-commit");
   assert.equal(githubCalls.filter(x=>x.method==="PUT").length,1);
   const logs=await auditEntries(10);
   assert(logs.some(x=>x.username==="job.friend"&&x.action==="checker.trigger"));
 }finally{
   globalThis.fetch=previousFetch;
   if(previousEnv===undefined)delete process.env.VERCEL_ENV;
   else process.env.VERCEL_ENV=previousEnv;
   if(previousPublishToken===undefined)delete process.env.GITHUB_PUBLISH_TOKEN;
   else process.env.GITHUB_PUBLISH_TOKEN=previousPublishToken;
 }
});


test("Only Owner can change Owner credentials and wrong current password is rejected",async()=>{
 const editor=await issueSession("job.friend","job_editor");
 const owner=await issueSession("owner","owner");
 const rEditor=res();
 await ownerPasswordHandler({...req(editor),method:"POST",body:{currentPassword:"test-owner-placeholder",newPassword:"NeverAllowedFromEditor-123"}},rEditor);
 assert.equal(rEditor.statusCode,403);
 const rWrong=res();
 await ownerPasswordHandler({...req(owner),method:"POST",body:{currentPassword:"incorrect-credential",newPassword:"FreshOwnerPassphrase-012345"}},rWrong);
 assert.equal(rWrong.statusCode,403);
 assert.equal(await ownerPasswordOverride(),null);
 assert.equal((await lookupSession(owner)).role,"owner");
 const rCrossSite=res();
 await ownerPasswordHandler({...req(owner),method:"POST",headers:{...req(owner).headers,origin:"https://untrusted.example"},body:{currentPassword:"test-owner-placeholder",newPassword:"FreshOwnerPassphrase-012345"}},rCrossSite);
 assert.equal(rCrossSite.statusCode,403);
});

test("Owner can rotate password in Preview; old environment password and all previous Owner sessions stop working",async()=>{
 const originalEnv=process.env.VERCEL_ENV;
 process.env.VERCEL_ENV="preview";
 try{
  const owner=await issueSession("owner","owner");
  const secondOwnerDevice=await issueSession("owner","owner");
  const editor=await issueSession("job.friend","job_editor");
  const updated=res();
  await ownerPasswordHandler({...req(owner),method:"POST",body:{currentPassword:"test-owner-placeholder",newPassword:"FreshOwnerPassphrase-012345"}},updated);
  assert.equal(updated.statusCode,200);
  assert.equal(updated.body.ok,true);
  assert.match(updated.headers["Set-Cookie"],/Max-Age=0/);
  assert.equal(await lookupSession(owner),null);
  assert.equal(await lookupSession(secondOwnerDevice),null);
  assert.equal((await lookupSession(editor)).role,"job_editor");
  assert.equal(await verifyCredentials("owner","test-owner-placeholder"),null);
  assert.equal((await verifyCredentials("owner","FreshOwnerPassphrase-012345")).role,"owner");
  const record=await ownerPasswordOverride();
  assert.equal(record.algorithm,"scrypt-16384");
  assert.equal(JSON.stringify(record).includes("FreshOwnerPassphrase-012345"),false);
  const auditRows=await auditEntries(30);
  assert(auditRows.some(row=>row.action==="owner.password.change"&&row.result==="success"));
  const newOwner=await issueSession("owner","owner");
  const secondUpdate=res();
  await ownerPasswordHandler({...req(newOwner),method:"POST",body:{currentPassword:"FreshOwnerPassphrase-012345",newPassword:"FinalOwnerPassphrase-0123456"}},secondUpdate);
  assert.equal(secondUpdate.statusCode,200);
  assert.equal(await verifyCredentials("owner","FreshOwnerPassphrase-012345"),null);
  assert.equal((await verifyCredentials("owner","FinalOwnerPassphrase-0123456")).role,"owner");
 }finally{
  if(originalEnv===undefined)delete process.env.VERCEL_ENV;
  else process.env.VERCEL_ENV=originalEnv;
 }
});
