import {requireAdmin,auditMutation} from "../../lib/admin-auth.js";

const DEFAULT_REPO="Chethan-Mns/Hdcareers";
const DEFAULT_BASE="main";
const JOBS_PATH="data/jobs.json";
const STATUS_PATH="data/availability-status.json";
const REVIEW_PATH="data/review-queue.json";
const APPROVED_BATCH_PATH="data/telegram-approved-batch.json";

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

function recompute(summary){
  const items=Array.isArray(summary.items)?summary.items:[];
  summary.checked=items.length;
  summary.active=items.filter(x=>x.state==="active").length;
  summary.expired=items.filter(x=>x.state==="expired").length;
  summary.review=items.filter(x=>x.state==="review").length;
  summary.changedExpired=items.filter(x=>x.state==="expired").length;
  return summary;
}

function slugify(value){
  return String(value||"job").toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-+|-+$/g,"").slice(0,80)||"job";
}

function today(){
  return new Date().toLocaleDateString("en-GB",{day:"2-digit",month:"short",year:"numeric"}).replace(/^0/,"");
}

function prepareApprovedJob(raw,jobs,now){
  const job={...(raw||{})};
  job.id=Math.max(0,...jobs.map(x=>Number(x.id)||0))+1;
  job.status="active";
  job.browserVerifiedAt=now;
  job.verifiedDate=today();

  const used=new Set(jobs.map(x=>String(x.page||"").toLowerCase()));
  let requested=String(job.page||"").trim();
  if(!(requested.startsWith("jobs/")&&requested.endsWith(".html")&&!requested.includes(".."))){
    requested="jobs/"+slugify(String(job.company||"")+"-"+String(job.role||""))+".html";
  }
  let page=requested;
  let suffix=2;
  while(used.has(page.toLowerCase())){
    page=requested.replace(/\.html$/,"-"+suffix+".html");
    suffix+=1;
  }
  job.page=page;
  return job;
}

async function readState(base,token){
  const ref=await github("/git/ref/heads/"+encodeURIComponent(base),token);
  const headSha=ref.object?.sha;
  if(!headSha)throw new Error("Could not read the current main commit.");

  const [jobsFile,statusFile,reviewFile]=await Promise.all([
    github("/contents/"+JOBS_PATH+"?ref="+encodeURIComponent(headSha),token),
    github("/contents/"+STATUS_PATH+"?ref="+encodeURIComponent(headSha),token),
    github("/contents/"+REVIEW_PATH+"?ref="+encodeURIComponent(headSha),token)
  ]);

  return {
    headSha,
    jobs:decode(jobsFile),
    summary:decode(statusFile),
    reviewQueue:decode(reviewFile)
  };
}

async function commitJsonFiles(base,headSha,changes,message,token){
  const parent=await github("/git/commits/"+headSha,token);
  const treeEntries=[];

  for(const [path,value] of Object.entries(changes)){
    const blob=await github("/git/blobs",token,{
      method:"POST",
      headers:{"content-type":"application/json"},
      body:JSON.stringify({
        content:JSON.stringify(value,null,2)+"\n",
        encoding:"utf-8"
      })
    });
    treeEntries.push({path,mode:"100644",type:"blob",sha:blob.sha});
  }

  const tree=await github("/git/trees",token,{
    method:"POST",
    headers:{"content-type":"application/json"},
    body:JSON.stringify({base_tree:parent.tree.sha,tree:treeEntries})
  });

  const commit=await github("/git/commits",token,{
    method:"POST",
    headers:{"content-type":"application/json"},
    body:JSON.stringify({message,tree:tree.sha,parents:[headSha]})
  });

  await github("/git/refs/heads/"+encodeURIComponent(base),token,{
    method:"PATCH",
    headers:{"content-type":"application/json"},
    body:JSON.stringify({sha:commit.sha,force:false})
  });

  return commit.sha;
}

export default async function handler(req,res){
  res.setHeader("Cache-Control","private, max-age=0, no-store");
  if(req.method!=="POST"){
    res.setHeader("Allow","POST");
    return res.status(405).json({error:"Method not allowed."});
  }
  if(!await requireAdmin(req,res))return;
  if(!sameOrigin(req))return res.status(403).json({error:"Invalid request origin."});

  const token=process.env.GITHUB_PUBLISH_TOKEN;
  if(!token)return res.status(503).json({error:"GITHUB_PUBLISH_TOKEN is not configured in Vercel."});

  const jobId=Number(req.body?.jobId);
  const action=String(req.body?.action||"");
  if(!Number.isFinite(jobId))return res.status(400).json({error:"A valid jobId is required."});
  if(!["expire","keep"].includes(action))return res.status(400).json({error:"action must be expire or keep."});

  const base=process.env.ADMIN_GITHUB_BASE||DEFAULT_BASE;

  try{await auditMutation(req,"job.review."+action,String(jobId));}
  catch{return res.status(503).json({error:"Audit logging unavailable. Review was not changed."});}

  for(let attempt=1;attempt<=5;attempt++){
    try{
      const {headSha,jobs,summary,reviewQueue}=await readState(base,token);
      if(!Array.isArray(jobs))throw new Error("data/jobs.json is not a JSON array.");
      if(!Array.isArray(reviewQueue))throw new Error("data/review-queue.json is not a JSON array.");
      if(!Array.isArray(summary.items))summary.items=[];

      const pendingIndex=reviewQueue.findIndex(x=>Number(x.reviewId)===jobId&&x.state==="review");
      const now=new Date().toISOString();

      if(pendingIndex>=0){
        const pending=reviewQueue[pendingIndex];

        if(action==="expire"){
          reviewQueue.splice(pendingIndex,1);
          await commitJsonFiles(
            base,
            headSha,
            {[REVIEW_PATH]:reviewQueue},
            "Reject review job: "+(pending.company||"Job")+" — "+(pending.role||"Opening"),
            token
          );
          return res.status(200).json({
            ok:true,
            action,
            jobId,
            company:pending.company||pending.job?.company||"",
            role:pending.role||pending.job?.role||"",
            status:"rejected",
            message:"Job rejected and removed from Needs Review. It was not published."
          });
        }

        const approved=prepareApprovedJob(pending.job,jobs,now);
        reviewQueue.splice(pendingIndex,1);
        await commitJsonFiles(
          base,
          headSha,
          {
            [JOBS_PATH]:[approved,...jobs],
            [REVIEW_PATH]:reviewQueue,
            [APPROVED_BATCH_PATH]:{approved:true,batchId:"admin-review-"+jobId+"-"+Date.now(),pages:[approved.page],approvedBy:"HD Careers Admin review"}
          },
          "Manual publish: "+(approved.company||"Job")+" — "+(approved.role||"Opening"),
          token
        );
        return res.status(200).json({
          ok:true,
          action,
          jobId:approved.id,
          company:approved.company,
          role:approved.role,
          status:"active",
          message:"Approved. The job has been moved back into the publishing flow."
        });
      }

      const job=jobs.find(x=>Number(x.id)===jobId);
      if(!job)return res.status(404).json({error:"Review item not found."});
      const result=summary.items.find(x=>Number(x.id)===jobId);

      if(action==="expire"){
        job.status="expired";
        job.verifiedDate=today();
        job.availabilityCheck={
          ...(job.availabilityCheck||{}),
          id:job.id,
          url:job.apply,
          checkedAt:now,
          state:"expired",
          reason:"Marked expired manually from HD Careers Admin review."
        };
        if(result){
          result.state="expired";
          result.reason="Marked expired manually from HD Careers Admin review.";
          result.checkedAt=now;
          result.manualReview="expire";
          result.manualReviewedAt=now;
        }
        summary.checkedAt=now;
        recompute(summary);

        await commitJsonFiles(
          base,
          headSha,
          {[JOBS_PATH]:jobs,[STATUS_PATH]:summary},
          "Manual expire: "+job.company+" — "+job.role,
          token
        );
      }else{
        job.browserVerifiedAt=now;
        job.verifiedDate=today();
        if(result){
          result.state="active";
          result.reason="Manually browser-verified in HD Careers Admin.";
          result.checkedAt=now;
          result.manualReview="keep";
          result.manualReviewedAt=now;
        }
        summary.checkedAt=now;
        recompute(summary);

        await commitJsonFiles(
          base,
          headSha,
          {[JOBS_PATH]:jobs,[STATUS_PATH]:summary},
          "Admin review active: "+job.company+" — "+job.role,
          token
        );
      }

      return res.status(200).json({
        ok:true,
        action,
        jobId,
        company:job.company,
        role:job.role,
        status:action==="expire"?"expired":"active",
        results:summary,
        message:action==="expire"?"Job marked expired. Site regeneration will follow automatically.":"Job manually verified active and removed from Needs Review."
      });
    }catch(error){
      const status=Number(error&&error.status);
      if((status===409||status===422)&&attempt<5)continue;
      return res.status(status===401||status===403?502:500).json({error:(error&&error.message)||"Could not resolve this review item."});
    }
  }

  return res.status(409).json({error:"The review changed while it was being saved. Please try again."});
}
