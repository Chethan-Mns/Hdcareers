import {requireAdmin,auditMutation} from "../../lib/admin-auth.js";
import {selectCandidates} from "../../lib/review-rules.js";
import {attachReviewedProof} from "../../lib/review-publish-proof.js";
import {redis} from "../../lib/admin-store.js";
import crypto from "node:crypto";

const DEFAULT_REPO = "Chethan-Mns/Hdcareers";
const DEFAULT_BASE = "main";
const MAX_JOBS = 20;
const CATS = new Set(["it","nonit","internship","apprenticeship","campus","remote","walkin","experienced","govt"]);
const CAT_FROM_LABEL = {
  "IT / Software":"it",
  "IT & Software":"it",
  "Non-IT":"nonit",
  "Non-IT Jobs":"nonit",
  "Non IT":"nonit",
  "Internship":"internship",
  "Apprenticeship":"apprenticeship",
  "Off-Campus":"campus",
  "Remote / WFH":"remote",
  "Walk-in":"walkin",
  "Experienced":"experienced",
  "Government":"govt",
  "Government Job":"govt"
};

function normalizeUrl(value){
  try{
    const u=new URL(String(value||""));
    u.hash="";
    return u.href.replace(/\/$/,"").toLowerCase();
  }catch{
    return String(value||"").trim().replace(/\/$/,"").toLowerCase();
  }
}

function initials(company){
  const parts=String(company||"HD").split(/\s+/).filter(Boolean);
  if(parts.length===1)return parts[0].slice(0,2).toUpperCase();
  return (parts[0][0]+parts[1][0]).toUpperCase();
}

function today(){
  return new Date().toLocaleDateString("en-GB",{day:"2-digit",month:"short",year:"numeric"}).replace(/^0/,"");
}

function deriveDomain(apply){
  try{return new URL(apply).hostname.replace(/^www\./,"");}catch{return "";}
}

function canonicalJob(input){
  const source=input&&input.source&&typeof input.source==="object"?input.source:{};
  const company=String(input.company||source.company||"").trim();
  const role=String(input.role||source.role||"").trim();
  const apply=String(input.apply||source.apply||source.sourceUrl||"").trim();
  const loc=String(input.loc||source.loc||"").trim();
  const expYears=String(input.exp||input.expYears||source.expYears||"0 years").trim()||"0 years";
  const catRaw=String(input.cat||source.cat||"it").trim();
  const cat=CAT_FROM_LABEL[catRaw]||catRaw;
  const sourceLogo=Array.isArray(source.logo)&&source.logo.length===2?source.logo:null;
  const publishStatus=String(input.publishStatus||input.status||source.status||"active").trim().toLowerCase();
  const expType=["experienced","fresher","not-specified"].includes(source.expType)
    ?source.expType
    :(/^0\s*years?$/i.test(expYears)||/fresher/i.test(expYears)?"fresher":"experienced");

  return {
    page:String(source.page||input.page||"").trim(),
    domain:String(source.domain||input.domain||deriveDomain(apply)).trim(),
    company,
    salary:String(input.salary||source.salary||"Not Disclosed").trim()||"Not Disclosed",
    logo:sourceLogo||[initials(company),"#0b6fe8"],
    logoUrl:String(input.logoUrl||source.logoUrl||"").trim(),
    role,
    roleTag:String(source.roleTag||input.roleTag||role).trim(),
    loc,
    locationFilter:String(source.locationFilter||input.locationFilter||loc).trim(),
    batch:String(input.batch||source.batch||"Not Specified").trim()||"Not Specified",
    elig:String(input.elig||source.elig||"").trim(),
    cat,
    expType,
    expYears,
    date:String(source.date||input.date||today()).trim(),
    desc:String(input.desc||source.desc||"").trim(),
    resp:Array.isArray(input.resp)?input.resp.map(x=>String(x).trim()).filter(Boolean):Array.isArray(source.resp)?source.resp.map(x=>String(x).trim()).filter(Boolean):[],
    apply,
    status:publishStatus,
    verifiedDate:String(input.verifiedDate||source.verifiedDate||today()).trim(),
    sourceName:String(input.sourceName||source.sourceName||(company+" official careers page")).trim(),
    skills:Array.isArray(input.skills)?input.skills.map(x=>String(x).trim()).filter(Boolean):Array.isArray(source.skills)?source.skills.map(x=>String(x).trim()).filter(Boolean):[],
    who:String(input.who||source.who||"Review the official requirements and apply if your education, experience and skills match the role.").trim(),
    closingAt:String(input.closingAt||source.closingAt||"").trim(),
    workMode:String(input.workMode||source.workMode||"Not Specified").trim()||"Not Specified",
    careerIconUrl:String(input.careerIconUrl||source.careerIconUrl||"").trim(),
    companyOverview:String(input.companyOverview||source.companyOverview||"").trim(),
    industry:String(input.industry||source.industry||"").trim(),
    headquarters:String(input.headquarters||source.headquarters||"").trim(),
    foundedYear:String(input.foundedYear||source.foundedYear||"").trim(),
    companyWebsite:String(input.companyWebsite||source.companyWebsite||"").trim(),
    careersUrl:String(input.careersUrl||source.careersUrl||"").trim(),
    jobId:String(input.jobId||source.jobId||"").trim(),
    selectionProcess:Array.isArray(input.selectionProcess)?input.selectionProcess.map(x=>String(x).trim()).filter(Boolean):Array.isArray(source.selectionProcess)?source.selectionProcess.map(x=>String(x).trim()).filter(Boolean):[],
    importantDates:Array.isArray(input.importantDates)?input.importantDates.map(x=>String(x).trim()).filter(Boolean):Array.isArray(source.importantDates)?source.importantDates.map(x=>String(x).trim()).filter(Boolean):[]
  };
}

function validateJob(job,index){
  const errors=[];
  if(!job.company)errors.push("company");
  if(!job.role)errors.push("role");
  if(!job.loc)errors.push("location");
  if(!job.elig)errors.push("eligibility");
  if(!job.desc)errors.push("description");
  if(!job.apply)errors.push("official apply URL");
  if(!job.domain)errors.push("domain");
  if(!job.resp.length)errors.push("responsibilities");
  if(!Array.isArray(job.skills))errors.push("skills");
  if(!job.who)errors.push("who should apply");
  if(!job.sourceName)errors.push("source");
  if(!job.verifiedDate)errors.push("verified date");
  if(job.status!=="active")errors.push("official source must be verified active before publishing");
  if(!CATS.has(job.cat))errors.push("category");
  if(!["fresher","experienced","not-specified"].includes(job.expType))errors.push("experience type");
  if(/candidate experience|careers? page|job search page/i.test(job.company))errors.push("review company name");
  try{
    const u=new URL(job.apply);
    if(u.protocol!=="https:")errors.push("HTTPS apply URL");
  }catch{errors.push("valid apply URL");}
  if(errors.length)throw new Error("Job "+(index+1)+" needs review: "+errors.join(", ")+".");
}

function sameOrigin(req){
  const origin=String(req.headers.origin||"");
  if(!origin)return true;
  const host=String(req.headers["x-forwarded-host"]||req.headers.host||"").toLowerCase();
  try{return new URL(origin).host.toLowerCase()===host;}catch{return false;}
}

async function github(path,token,options={}){
  const response=await fetch("https://api.github.com/repos/"+(process.env.ADMIN_GITHUB_REPO||DEFAULT_REPO)+path,{
    ...options,
    headers:{
      "accept":"application/vnd.github+json",
      "authorization":"Bearer "+token,
      "x-github-api-version":"2022-11-28",
      "user-agent":"HD-Careers-Admin-Publisher",
      ...(options.headers||{})
    }
  });
  const text=await response.text();
  let data={};
  try{data=text?JSON.parse(text):{};}catch{data={message:text};}
  if(!response.ok){
    const error=new Error(data.message||("GitHub returned HTTP "+response.status));
    error.status=response.status;
    throw error;
  }
  return data;
}

export default async function handler(req,res){
  res.setHeader("Cache-Control","no-store");

  if(!["GET","POST"].includes(req.method)){
    res.setHeader("Allow","GET, POST");
    return res.status(405).json({error:"Method not allowed"});
  }

  if(!sameOrigin(req))return res.status(403).json({error:"Invalid request origin."});
  if(!await requireAdmin(req,res,["owner","job_editor"]))return;
  if(req.method==="POST"&&process.env.VERCEL_ENV==="preview")return res.status(403).json({error:"Preview is read-only; website and Telegram publishing is disabled."});

  const token=process.env.GITHUB_PUBLISH_TOKEN;
  if(!token)return res.status(503).json({error:"GITHUB_PUBLISH_TOKEN is not configured in Vercel yet."});

  try{
    const base=process.env.ADMIN_GITHUB_BASE||DEFAULT_BASE;
    const readJson=async(path,defaultValue)=>{
      try{
        const doc=await github("/contents/"+path+"?ref="+encodeURIComponent(base),token);
        return JSON.parse(Buffer.from(String(doc.content||"").replace(/\n/g,""),"base64").toString("utf8"));
      }catch(e){if(e.status===404&&defaultValue!==undefined)return defaultValue;throw e}
    };
    if(req.method==="GET"){
      const batch=await readJson("data/daily-review-batch.json",{});
      const saved=await readJson("data/jobs.json",[]);
      const ledger=await readJson("data/telegram-deliveries.json",{});
       const hourly=await readJson("data/telegram-hourly-queue.json",{items:[]});
       const queueItems=Array.isArray(hourly.items)?hourly.items:[];
      const urls=new Set(saved.map(x=>normalizeUrl(x.apply)));
      const allCandidates=[...(batch.priority||[]),...(batch.backup||[])];
      const publishedCandidateIds=allCandidates.filter(x=>urls.has(normalizeUrl(x.job?.apply||x.apply))).map(x=>String(x.id));
      const publishedIds=new Set(publishedCandidateIds);
      const selections=Array.isArray(batch.publication?.candidateIds)?batch.publication.candidateIds:[];
      // A GitHub data commit is not proof that the public production page is live.
      const production=await Promise.all(selections.map(async id=>{
        const candidate=allCandidates.find(c=>String(c.id)===String(id));
        const existing=saved.find(x=>normalizeUrl(x.apply)===normalizeUrl(candidate?.job?.apply||candidate?.apply));
         const page=String(existing?.page||candidate?.job?.page||"").replace(/^\//,"");
        if(!/^jobs\/[a-z0-9-]+\.html$/.test(page))return {id,live:false};
        const controller=new AbortController();
        const timeout=setTimeout(()=>controller.abort(),4000);
        try{
          const response=await fetch("https://hdcareers.in/"+page,{
            cache:"no-store",signal:controller.signal,headers:{"Accept":"text/html"}
          });
          if(!response.ok)return {id,live:false};
          const html=(await response.text()).replace(/&amp;/g,"&");
          return {id,live:Boolean(candidate?.job?.apply&&html.includes(String(candidate.job.apply)))};
        }catch{return {id,live:false}}
        finally{clearTimeout(timeout)}
      }));
      const livePages=new Set(production.filter(x=>x.live).map(x=>String(x.id)));
      const stages=selections.map(id=>{
        const c=[...(batch.priority||[]),...(batch.backup||[])].find(x=>String(x.id)===id);
        const existing=saved.find(x=>normalizeUrl(x.apply)===normalizeUrl(c?.job?.apply||c?.apply));
         const page=String(existing?.page||c?.job?.page||"").replace(/^\//,"");
         const queued=queueItems.find(x=>x?.page===page);
        const entries=Object.values(ledger).filter(x=>x&&x.page===page);
        const last=entries.at(-1)||{};
        return {candidateId:id,company:c?.company||c?.job?.company||"",role:c?.role||c?.job?.role||"",
          github:batch.status==="submitted"?"accepted":batch.status==="published"?"completed":"not_submitted",
          website:livePages.has(String(id))?"live":urls.has(normalizeUrl(c?.job?.apply))?"data-committed":"pending",
          vercel:livePages.has(String(id))?"production-page-confirmed":"unconfirmed",telegram:last.status||queued?.status||"not_queued",telegramMessageId:last.messageId||queued?.messageId||null,
          note:last.status==="uncertain"?"Check Telegram manually before retrying.":""};
      });
      let workflow={state:"not_checked",url:null,conclusion:null};
      try{
        const runs=await github("/actions/workflows/admin-job-generator.yml/runs?per_page=15",token);
        const since=Date.parse(batch.submittedAt||"");
        const run=(runs.workflow_runs||[]).find(x=>x.event==="repository_dispatch"&&Number.isFinite(since)&&Date.parse(x.created_at)>=since-60000);
        if(run)workflow={state:run.status,url:run.html_url,conclusion:run.conclusion,runId:run.id,exactMatch:false};
      }catch(e){workflow={state:"unavailable",url:null,conclusion:null,reason:"GitHub workflow lookup failed"}}
      return res.status(200).json({batchId:batch.batchId||null,status:batch.status||"waiting",
        publishedCount:stages.filter(x=>x.website==="live").length,
        dataCommittedCount:stages.filter(x=>x.website==="live"||x.website==="data-committed").length,
        alreadyPublishedCount:publishedCandidateIds.length,publishedCandidateIds,
        telegramDelivered:stages.filter(x=>x.telegram==="delivered").length,
         telegramHourlyPending:stages.filter(x=>["pending","sending"].includes(x.telegram)).length,
        workflow,stages,observedAt:new Date().toISOString(),
        warning:"GitHub workflow matching is approximate. Production page evidence is checked directly on hdcareers.in. Vercel commit identity is not independently verified."});
    }
    const fromTest=String(req.body?.testInboxId||"")==="two-job-preview-20261017";
    const testKey="hdadmin:manual-review:v1:"+(process.env.VERCEL_ENV==="preview"?"preview":"production")+":test-two-jobs";
    let testInbox=null;
    if(fromTest){
      const raw=await redis("GET",testKey);
      if(!raw)return res.status(404).json({error:"Two-job test inbox is not staged."});
      testInbox=JSON.parse(raw);
      if(testInbox.id!==req.body.testInboxId||testInbox.status!=="reviewing")
        return res.status(409).json({error:"This test inbox has already been submitted."});
      const ids=req.body.candidateIds;
      if(!Array.isArray(ids)||ids.length<1||ids.length>2||new Set(ids).size!==ids.length)
        return res.status(400).json({error:"Select one or two test jobs."});
      const picked=ids.map(id=>testInbox.jobs.find(j=>j.id===id));
      if(picked.some(j=>!j||j.reviewedStatus!=="live"||!j.reviewedAt||j.status!=="review"))
        return res.status(409).json({error:"Only manually verified Live test jobs can be published."});
      if(picked.some(j=>!j.apply?.startsWith("https://")||!j.role||!j.company||!j.desc||!j.elig||!Array.isArray(j.resp)||j.resp.length===0))
        return res.status(400).json({error:"Selected test jobs lack verified source content."});
      req.body.jobs=picked.map(j=>({...j,status:"active",manualLiveVerifiedAt:j.reviewedAt,manualLiveVerifiedUrl:j.apply}));
    }
    const fromReview=Boolean(req.body?.batchId);
    let reviewBatch=null;
    const selectedIds=fromReview?req.body.candidateIds:null;
    let submitted=Array.isArray(req.body?.jobs)?req.body.jobs:[];
    if(fromReview){
      reviewBatch=await readJson("data/daily-review-batch.json");
      if(reviewBatch.batchId!==req.body.batchId||reviewBatch.status!=="reviewing"){
        return res.status(409).json({error:"Review batch changed or was already submitted. Refresh before publishing."});
      }
      submitted=selectCandidates(reviewBatch,selectedIds).map(x=>x.job);
    }
    if(!submitted.length)return res.status(400).json({error:"Select at least one job to publish."});
    if(submitted.length>(fromReview?10:MAX_JOBS))return res.status(400).json({error:"Maximum "+(fromReview?10:MAX_JOBS)+" jobs per deployment."});
    const normalized=submitted.map(canonicalJob);
    const incoming=fromReview?attachReviewedProof(normalized,reviewBatch,selectedIds):normalized;
    incoming.forEach(validateJob);

    const file=await github("/contents/data/jobs.json?ref="+encodeURIComponent(base),token);
    const current=JSON.parse(Buffer.from(String(file.content||"").replace(/\n/g,""),"base64").toString("utf8"));
    if(!Array.isArray(current))throw new Error("data/jobs.json is not a JSON array.");

    const existingUrls=new Set(current.map(j=>normalizeUrl(j.apply)));
    const existingPairs=new Set(current.map(j=>(String(j.company||"")+"\n"+String(j.role||"")).toLowerCase()));
    const incomingUrls=new Set();
    const incomingPairs=new Set();
    const duplicates=[];

    for(const job of incoming){
      const url=normalizeUrl(job.apply);
      const pair=(job.company+"\n"+job.role).toLowerCase();
      if(existingUrls.has(url)||incomingUrls.has(url)||existingPairs.has(pair)||incomingPairs.has(pair)){
        duplicates.push(job.company+" — "+job.role);
      }
      incomingUrls.add(url);
      incomingPairs.add(pair);
    }

    if(duplicates.length)return res.status(409).json({error:"Duplicate job detected.",duplicates});

    const requestId=fromReview?crypto.createHash("sha256").update(reviewBatch.batchId+"|"+selectedIds.join("|")).digest("hex").slice(0,24):
      fromTest?crypto.createHash("sha256").update(testInbox.id+"|"+req.body.candidateIds.join("|")).digest("hex").slice(0,24):null;
    const telegramDeliveryMode=req.body?.telegramDeliveryMode==="hourly"?"hourly":"instant";
     const payload=JSON.stringify({event_type:"admin_publish_jobs",client_payload:{jobs:incoming,telegramDeliveryMode,...(requestId?{reviewBatchId:reviewBatch.batchId,reviewCandidateIds:selectedIds,requestId}:{})}});
    if(Buffer.byteLength(payload,"utf8")>60000){
      return res.status(413).json({error:"Selected job data is too large for one deployment. Publish fewer jobs at a time."});
    }

    await auditMutation(req,"jobs.publish",incoming.map(j=>j.company+" - "+j.role).join("; ").slice(0,150));
    const lockKey=requestId?"hdreview:dispatch:"+process.env.VERCEL_ENV+":"+(fromTest?testInbox.id:reviewBatch.batchId):null;
    if(lockKey){
      const acquired=await redis("SET",lockKey,requestId,"NX","EX",86400);
      if(acquired!=="OK")return res.status(409).json({error:"This review batch has already started publishing. Check the tracker; never resend a pending batch."});
    }
    try{
      await github("/dispatches",token,{
        method:"POST",
        headers:{"content-type":"application/json"},
        body:payload
      });
    }catch(e){
      // A timeout can occur after GitHub accepts the dispatch. Keep the lock
      // rather than risking a duplicate publish when the outcome is unknown.
      if(lockKey&&Number(e.status)>=400&&Number(e.status)<500)await redis("DEL",lockKey);
      throw e;
    }

    if(fromTest){
      testInbox.status="submitted";
      testInbox.requestId=requestId;
      testInbox.submittedAt=new Date().toISOString();
      testInbox.selectedIds=req.body.candidateIds;
      try{await redis("SET",testKey,JSON.stringify(testInbox),"EX",7*86400)}
      catch(e){return res.status(202).json({ok:true,queued:true,requestId,message:"GitHub accepted dispatch, but test status could not be saved. Do not retry; verify delivery manually."})}
    }
    return res.status(202).json({
      ok:true,
      queued:true,
      count:incoming.length,
      requestId,
      message:"GitHub accepted the publishing request. Website deployment and Telegram delivery are not confirmed yet."
    });
  }catch(error){
    const status=Number(error&&error.status);
    const code=status===401||status===403?502:400;
    return res.status(code).json({error:(error&&error.message)||"Could not start the production deployment."});
  }
}
