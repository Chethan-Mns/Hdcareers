import {requireAdmin,auditMutation} from "../../lib/admin-auth.js";
import {redis,audit} from "../../lib/admin-store.js";
import crypto from "node:crypto";
import {notifyTwoJobReview} from "../../lib/admin-push-handler.js";

const PREFIX="hdadmin:manual-review:v1:"+(process.env.VERCEL_ENV==="preview"?"preview":"production")+":";
const ROOT="https://api.github.com/repos/"+(process.env.ADMIN_GITHUB_REPO||"Chethan-Mns/Hdcareers");
const SOURCE="data/testing/two-job-publish-preview-20261017.json";
async function readStaged(){
 const token=process.env.GITHUB_PUBLISH_TOKEN;
 if(!token)throw Error("Publishing GitHub token missing");
 const r=await fetch(ROOT+"/contents/"+SOURCE+"?ref=main",{headers:{Authorization:"Bearer "+token,Accept:"application/vnd.github+json"},signal:AbortSignal.timeout(8000)});
 if(!r.ok)throw Error("Staged job draft unavailable: "+r.status);
 const file=await r.json();
 const data=JSON.parse(Buffer.from(file.content.split(String.fromCharCode(10)).join(""),"base64").toString());
 if(!Array.isArray(data.jobs)||data.jobs.length!==2||data.publishAuthorized!==false)throw Error("Invalid staging snapshot");
 return data;
}
export default async function handler(req,res){
 res.setHeader("Cache-Control","private, no-store");
 if(!["GET","POST"].includes(req.method)){res.setHeader("Allow","GET, POST");return res.status(405).json({error:"Method not allowed"});}
 const secret=String(process.env.ANDROID_PUSH_DISPATCH_SECRET||"");
 const provided=String(req.headers["x-hd-push-key"]||"");
 const validSecret=secret.length>=32&&provided.length===secret.length&&
  crypto.timingSafeEqual(Buffer.from(provided),Buffer.from(secret));
 const automated=req.method==="POST"&&req.body?.action==="stage_from_github"&&validSecret;
 if(!automated&&!await requireAdmin(req,res,["owner","job_editor"]))return;
 if(req.method==="POST"&&process.env.VERCEL_ENV==="preview")return res.status(403).json({error:"Read-only preview"});
 if(req.method==="POST"&&!automated){
  const origin=String(req.headers.origin||"");
  const host=String(req.headers["x-forwarded-host"]||req.headers.host||"").toLowerCase();
  try{if(origin&&new URL(origin).host.toLowerCase()!==host)return res.status(403).json({error:"Invalid origin"});}
  catch{return res.status(403).json({error:"Invalid origin"});}
 }
 try{
  const key=PREFIX+"test-two-jobs";
  if(req.method==="GET"){
   const raw=await redis("GET",key);
   const data=raw?JSON.parse(raw):null;
   if(!data||data.status!=="submitted")return res.status(200).json({ok:true,staged:data,stages:[]});
   const token=process.env.GITHUB_PUBLISH_TOKEN;
   const source=async path=>{
    const r=await fetch(ROOT+"/contents/"+path+"?ref=main",{headers:{Authorization:"Bearer "+token,Accept:"application/vnd.github+json"},signal:AbortSignal.timeout(8000)});
    if(!r.ok)throw Error("Could not read "+path);
    const v=await r.json();return JSON.parse(Buffer.from(v.content.split(String.fromCharCode(10)).join(""),"base64").toString());
   };
   try{
    const [jobs,ledger]=await Promise.all([source("data/jobs.json"),source("data/telegram-deliveries.json")]);
    const stages=await Promise.all(data.jobs.filter(j=>data.selectedIds.includes(j.id)).map(async j=>{
      const existing=jobs.find(x=>String(x.apply).replace(new RegExp("/$"),"")===String(j.apply).replace(new RegExp("/$"),""));
      const page=String(existing?.page||"").replace(new RegExp("^/"),"");
      let website="pending";
      if(existing){
       website="data-committed";
       if(page.startsWith("jobs/")&&page.endsWith(".html")&&!page.includes("..")){
        try{
         const r=await fetch("https://hdcareers.in/"+page,{signal:AbortSignal.timeout(6000),headers:{"Cache-Control":"no-cache"}});
         const html=r.ok?await r.text():"";
         if(r.ok&&html.toLowerCase().includes(j.role.toLowerCase()))website="live";
        }catch{}
       }
      }
      const receipts=Object.values(ledger||{}).filter(x=>x&&x.page===page&&page);
      const last=receipts.at(-1)||{};
      return {candidateId:j.id,company:j.company,role:j.role,apply:j.apply,page,github:existing?"data-committed":"dispatched-unconfirmed",
       website,telegram:last.status||"not-confirmed",telegramMessageId:last.messageId||null};
    }));
    return res.status(200).json({ok:true,staged:data,stages,observedAt:new Date().toISOString(),warning:"GitHub workflow execution not independently matched; website verified by actual public page, Telegram by delivery ledger."});
   }catch(e){return res.status(200).json({ok:true,staged:data,stages:[],warning:"Progress evidence temporarily unavailable: "+e.message});}
  }
  if(req.body?.action==="reset"){
   const raw=await redis("GET",key);
   if(raw){
    const current=JSON.parse(raw);
    if(current.status!=="reviewing")return res.status(409).json({error:"Previously submitted test jobs cannot be silently cleared; preserve publishing evidence."});
   }
   await redis("DEL",key);
   await auditMutation(req,"two_job_inbox.reset","unsubmitted test inbox");
   return res.status(200).json({ok:true,cleared:true});
  }
  if(req.body?.action==="review"){
   const raw=await redis("GET",key);
   if(!raw)return res.status(404).json({error:"Stage the two jobs before reviewing."});
   const data=JSON.parse(raw);
   if(data.status!=="reviewing")return res.status(409).json({error:"The test inbox was already submitted."});
   const job=data.jobs.find(x=>x.id===req.body.jobId);
   if(!job)return res.status(404).json({error:"Job not in this test inbox"});
   if(!["live","expired","unsure"].includes(req.body.decision))return res.status(400).json({error:"Invalid review decision"});
   job.reviewedStatus=req.body.decision;
   job.reviewedAt=new Date().toISOString();
   await redis("SET",key,JSON.stringify(data),"EX",7*86400);
   await auditMutation(req,"two_job_inbox.review",job.id+":"+job.reviewedStatus);
   return res.status(200).json({ok:true,staged:data});
  }
  const action=automated?"replace":req.body?.action;
  if(!["stage","replace"].includes(action))return res.status(400).json({error:"Unsupported test inbox action"});
  const staged=await readStaged();
  if(action==="replace"){
   const prior=await redis("GET",key);
   if(prior){
    const previous=JSON.parse(prior);
    if(previous.status!=="reviewing")
     return res.status(409).json({error:"Cannot replace submitted test jobs. Preserve publication evidence."});
    const unchanged=previous.jobs.length===staged.jobs.length&&
     previous.jobs.every((j,i)=>j.apply===staged.jobs[i].apply);
    if(unchanged){
     const push=await notifyTwoJobReview(automated?null:req.adminUser.username,previous.id);
     return res.status(200).json({ok:true,unchanged:true,count:previous.jobs.length,
      notification:push.accepted>0?"accepted_by_fcm":"not_accepted",push,publishEnabled:false});
    }
    if(automated&&previous.jobs.some(j=>j.reviewedStatus!=="unreviewed"))
     return res.status(409).json({error:"Owner has already reviewed a previous test job; automated replacement refused."});
    await redis("DEL",key);
   }
  }
  const origin=String(req.headers.origin||"");
  if(!automated&&origin&&new URL(origin).host!==String(req.headers["x-forwarded-host"]||req.headers.host))return res.status(403).json({error:"Invalid origin"});
  const jobs=staged.jobs.map((job,i)=>({...job,id:"two-job-preview-20261017-"+(i+1),reviewedStatus:"unreviewed",reviewedAt:null}));
  const data={id:"two-job-preview-20261017",status:"reviewing",createdAt:new Date().toISOString(),jobs,publishAuthorized:false};
  const value=await redis("SET",key,JSON.stringify(data),"NX","EX",7*86400);
  if(value!=="OK")return res.status(409).json({error:"Test inbox already staged; refresh instead of resending"});
  if(automated)await audit({username:"github-actions",role:"automation",action:"two_job_inbox.stage",target:data.id,result:"attempt"});
  else await auditMutation(req,"two_job_inbox.stage",data.id);
  const push=await notifyTwoJobReview(automated?null:req.adminUser.username,data.id);
  return res.status(201).json({ok:true,inboxId:data.id,count:jobs.length,notification:push.accepted>0?"accepted_by_fcm":"not_accepted",push,publishEnabled:false});
 }catch(e){return res.status(503).json({error:e.message||"Inbox unavailable"})}
}