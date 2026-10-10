import {requireAdmin,auditMutation} from "../../lib/admin-auth.js";

const DEFAULT_REPO="Chethan-Mns/Hdcareers";
const DEFAULT_BASE="main";
const WORKFLOW="job-availability.yml";
const TRIGGER_PATH="data/availability-trigger.json";
const STATUS_PATH="data/availability-status.json";
const REVIEW_PATH="data/review-queue.json";

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
      ...(token?{authorization:"Bearer "+token}:{}),
      "x-github-api-version":"2022-11-28",
      "user-agent":"HD-Careers-Admin-Availability",
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

function decodeFile(file){
  try{return JSON.parse(Buffer.from(String(file.content||"").replace(/\n/g,""),"base64").toString("utf8"))}catch{return {}}
}

function runSummary(run,trigger){
  if(!run)return null;
  const created=run.created_at?new Date(run.created_at):null;
  const requested=trigger?.requestedAt?new Date(trigger.requestedAt):null;
  let source=run.event==="schedule"?"Scheduled":run.event==="workflow_dispatch"?"Manual":run.event==="push"?"Repository update":"GitHub Actions";
  if(run.event==="push"&&created&&requested&&Math.abs(created-requested)<5*60*1000)source="Admin manual";
  return {
    id:run.id,
    runNumber:run.run_number,
    status:run.status,
    conclusion:run.conclusion||null,
    event:run.event,
    source,
    createdAt:run.created_at||null,
    updatedAt:run.updated_at||null,
    url:run.html_url||null
  };
}

export default async function handler(req,res){
  res.setHeader("Cache-Control","private, max-age=0, no-store");
  if(!await requireAdmin(req,res,["owner","job_editor"]))return;
  if(!["GET","POST"].includes(req.method)){
    res.setHeader("Allow","GET, POST");
    return res.status(405).json({error:"Method not allowed."});
  }
  if(req.method==="POST"&&process.env.VERCEL_ENV==="preview")return res.status(403).json({error:"Preview is read-only. Production job changes are disabled."});
  if(req.method==="POST"&&!sameOrigin(req))return res.status(403).json({error:"Invalid request origin."});

  const token=process.env.GITHUB_PUBLISH_TOKEN;
  const base=process.env.ADMIN_GITHUB_BASE||DEFAULT_BASE;

  try{
    if(req.method==="POST"){
      if(!token)return res.status(503).json({error:"GITHUB_PUBLISH_TOKEN is not configured in Vercel."});
      const runs=await github("/actions/workflows/"+WORKFLOW+"/runs?branch="+encodeURIComponent(base)+"&per_page=1",token);
      const latest=runs.workflow_runs?.[0];
      if(latest&&["queued","in_progress"].includes(latest.status)){
        return res.status(409).json({error:"The expired-job checker is already running.",run:runSummary(latest,{})});
      }

      const file=await github("/contents/"+TRIGGER_PATH+"?ref="+encodeURIComponent(base),token);
      const payload={
        requestedAt:new Date().toISOString(),
        reason:"Manual expired-job check from HD Careers Admin",
        nonce:Date.now()
      };
      const body={
        message:"Trigger manual job availability check",
        content:Buffer.from(JSON.stringify(payload,null,2)+"\n","utf8").toString("base64"),
        sha:file.sha,
        branch:base
      };
      await auditMutation(req,"checker.trigger",WORKFLOW);
      const update=await github("/contents/"+TRIGGER_PATH,token,{
        method:"PUT",
        headers:{"content-type":"application/json"},
        body:JSON.stringify(body)
      });
      return res.status(202).json({
        ok:true,
        queued:true,
        requestedAt:payload.requestedAt,
        commitSha:update.commit?.sha||null,
        message:"Expired-job checker queued."
      });
    }

    const [file,statusFile,reviewFile,runs]=await Promise.all([
      github("/contents/"+TRIGGER_PATH+"?ref="+encodeURIComponent(base),token).catch(()=>null),
      github("/contents/"+STATUS_PATH+"?ref="+encodeURIComponent(base),token).catch(()=>null),
      github("/contents/"+REVIEW_PATH+"?ref="+encodeURIComponent(base),token).catch(()=>null),
      github("/actions/workflows/"+WORKFLOW+"/runs?branch="+encodeURIComponent(base)+"&per_page=5",token).catch(()=>({workflow_runs:[]}))
    ]);
    const trigger=file?decodeFile(file):{};
    const checker=statusFile?decodeFile(statusFile):{};
    const reviewQueue=reviewFile?decodeFile(reviewFile):[];
    const pendingReviews=(Array.isArray(reviewQueue)?reviewQueue:[])
      .filter(x=>x&&x.state==="review")
      .map(x=>({
        id:Number(x.reviewId),
        company:x.company||x.job?.company||"",
        role:x.role||x.job?.role||"",
        page:x.page||x.job?.page||"",
        url:x.url||x.job?.apply||"",
        state:"review",
        reason:x.reason||"Manual verification required before publishing.",
        checkedAt:x.checkedAt||x.queuedAt||null,
        reviewType:"new_job",
        pendingNew:true,
        source:x.source||"publishing"
      }));
    const list=Array.isArray(runs.workflow_runs)?runs.workflow_runs:[];
    const latest=list[0]||null;
    const lastCompleted=list.find(x=>x.status==="completed")||null;
    const latestSummary=runSummary(latest,trigger);
    const summaryTime=checker.checkedAt?new Date(checker.checkedAt).getTime():0;
    const runTime=latestSummary?.createdAt?new Date(latestSummary.createdAt).getTime():0;

    return res.status(200).json({
      configured:Boolean(token),
      trigger:{
        requestedAt:trigger.requestedAt||null,
        reason:trigger.reason||null
      },
      latestRun:latestSummary,
      lastCompletedRun:runSummary(lastCompleted,trigger),
      results:{
        checkedAt:checker.checkedAt||null,
        checked:Number(checker.checked||0)+pendingReviews.length,
        active:Number(checker.active||0),
        expired:Number(checker.expired||0),
        review:Number(checker.review||0)+pendingReviews.length,
        changedExpired:Number(checker.changedExpired||checker.expired||0),
        items:[...(Array.isArray(checker.items)?checker.items:[]),...pendingReviews],
        current:!latestSummary||latestSummary.status!=="completed"||summaryTime>=runTime
      }
    });
  }catch(error){
    const status=Number(error&&error.status);
    return res.status(status===401||status===403?502:500).json({error:(error&&error.message)||"Could not access the job availability checker."});
  }
}
