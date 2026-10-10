import test from "node:test";
import assert from "node:assert/strict";
import {verifyCredentials,createAdminSession,requireAdmin} from "../lib/admin-auth.js";
import {createEditor,getUser,lookupSession,issueSession,setEditorState,removeSession,audit,auditEntries} from "../lib/admin-store.js";
import teamHandler from "../api/admin/team.js";
import auditHandler from "../api/admin/audit.js";
import trafficHandler from "../api/admin/traffic.js";
import publishHandler from "../api/admin/publish.js";

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
