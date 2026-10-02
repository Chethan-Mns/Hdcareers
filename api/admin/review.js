import {requireAdmin} from "../../lib/admin-auth.js";

const DEFAULT_REPO="Chethan-Mns/Hdcareers";
const DEFAULT_BASE="main";
const JOBS_PATH="data/jobs.json";
const STATUS_PATH="data/availability-status.json";

function sameOrigin(req){
  const origin=String(req.headers.origin||"");
  if(!origin)return true;
  const host=String(req.headers["x-forwarded-host"]||req.headers.host||"").toLowerCase();
  try{return new URL(origin).host.toLowerCase()===host}catch{return false}
}

async function github(path,token,options={}){
  const response=await fetch("https://api.github.com/repos/"+(process.env.ADMIN_GITHUB_REPO||DEFAULT_REPO)+path,{
    ...options,
    headers:{
      accept:"application/vnd.github+json",
      authorization:"Bearer "+token,
      "x-github-api-version":"2022-11-28",
      "user-agent":"HD-Careers-Admin-Review",
      ...(options.headers||{})
    }
  });
  const text=await response.text();
  let data={};
  try{data=text?JSON.parse(text):{}}catch{data={message:text}}
  if(!response.ok){
    const error=new Error(data.message||("GitHub returned HTTP "+response.status));
    error.status=response.status;
    throw error;
  }
  return data;
}

function decode(file){
  return JSON.parse(Buffer.from(String(file.content||"").replace(/\n/g,""),"base64").toString("utf8"));
}

function encode(value){
  return Buffer.from(JSON.stringify(value,null,2)+"\n","utf8").toString("base64");
}

function recompute(summary){
  const items=Array.isArray(summary.items)?summary.items:[];
  summary.checked=items.length;
  summary.active=items.filter(x=>x.state==="active").length;
  summary.expired=items.filter(x=>x.state==="expired").length;
  summary.review=items.filter(x=>x.state==="review").length;
  summary.changedExpired=items.filter(x=>x.state==="expired").length;
  return summary;
}

export default async function handler(req,res){
  res.setHeader("Cache-Control","private, max-age=0, no-store");
  if(req.method!=="POST"){
    res.setHeader("Allow","POST");
    return res.status(405).json({error:"Method not allowed."});
  }
  if(!requireAdmin(req,res))return;
  if(!sameOrigin(req))return res.status(403).json({error:"Invalid request origin."});

  const token=process.env.GITHUB_PUBLISH_TOKEN;
  if(!token)return res.status(503).json({error:"GITHUB_PUBLISH_TOKEN is not configured in Vercel."});

  const jobId=Number(req.body?.jobId);
  const action=String(req.body?.action||"");
  if(!Number.isFinite(jobId))return res.status(400).json({error:"A valid jobId is required."});
  if(!["expire","keep"].includes(action))return res.status(400).json({error:"action must be expire or keep."});

  const base=process.env.ADMIN_GITHUB_BASE||DEFAULT_BASE;
  try{
    const [jobsFile,statusFile]=await Promise.all([
      github("/contents/"+JOBS_PATH+"?ref="+encodeURIComponent(base),token),
      github("/contents/"+STATUS_PATH+"?ref="+encodeURIComponent(base),token)
    ]);
    const jobs=decode(jobsFile);
    const summary=decode(statusFile);
    if(!Array.isArray(jobs))throw new Error("data/jobs.json is not a JSON array.");
    if(!Array.isArray(summary.items))summary.items=[];

    const job=jobs.find(x=>Number(x.id)===jobId);
    if(!job)return res.status(404).json({error:"Job not found."});

    const result=summary.items.find(x=>Number(x.id)===jobId);
    const now=new Date().toISOString();

    if(action==="expire"){
      job.status="expired";
      job.verifiedDate=new Date().toLocaleDateString("en-GB",{day:"2-digit",month:"short",year:"numeric"}).replace(/^0/,"");
      job.availabilityCheck={
        ...(job.availabilityCheck||{}),
        id:job.id,
        url:job.apply,
        checkedAt:now,
        state:"expired",
        reason:"Marked expired manually from HD Careers Admin review."
      };

      await github("/contents/"+JOBS_PATH,token,{
        method:"PUT",
        headers:{"content-type":"application/json"},
        body:JSON.stringify({
          message:"Mark "+job.company+" — "+job.role+" expired from admin review",
          content:encode(jobs),
          sha:jobsFile.sha,
          branch:base
        })
      });

      if(result){
        result.state="expired";
        result.reason="Marked expired manually from HD Careers Admin review.";
        result.checkedAt=now;
        result.manualReview="expire";
        result.manualReviewedAt=now;
      }
    }else{
      if(result){
        result.state="active";
        result.reason="Manually reviewed in HD Careers Admin — no change requested.";
        result.checkedAt=now;
        result.manualReview="keep";
        result.manualReviewedAt=now;
      }
    }

    summary.checkedAt=now;
    recompute(summary);

    const latestStatus=await github("/contents/"+STATUS_PATH+"?ref="+encodeURIComponent(base),token);
    await github("/contents/"+STATUS_PATH,token,{
      method:"PUT",
      headers:{"content-type":"application/json"},
      body:JSON.stringify({
        message:(action==="expire"?"Resolve expired":"Keep active")+" job review #"+jobId,
        content:encode(summary),
        sha:latestStatus.sha,
        branch:base
      })
    });

    return res.status(200).json({
      ok:true,
      action,
      jobId,
      company:job.company,
      role:job.role,
      status:action==="expire"?"expired":"active",
      results:summary,
      message:action==="expire"?"Job marked expired. Site regeneration will follow automatically.":"Job kept active and removed from Needs Review."
    });
  }catch(error){
    const status=Number(error&&error.status);
    return res.status(status===401||status===403?502:500).json({error:(error&&error.message)||"Could not resolve this review item."});
  }
}
