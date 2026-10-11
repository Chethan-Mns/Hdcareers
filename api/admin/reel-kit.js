import {requireAdmin} from "../../lib/admin-auth.js";

const REPO="Chethan-Mns/Hdcareers";
const BASE="main";
const PICK="data/reel-selection.json";
const JOBS="data/jobs.json";

function originAllowed(req){
  if(req.headers["sec-fetch-site"]==="cross-site")return false;
  const origin=String(req.headers.origin||"");
  if(!origin)return true;
  const host=String(req.headers["x-forwarded-host"]||req.headers.host||"").toLowerCase();
  try{return new URL(origin).host.toLowerCase()===host}catch{return false}
}
async function github(path,token,options={}){
  const response=await fetch("https://api.github.com/repos/"+(process.env.ADMIN_GITHUB_REPO||REPO)+path,{
    ...options,
    headers:{"accept":"application/vnd.github+json","x-github-api-version":"2022-11-28","user-agent":"HD-Careers-Reel-Kit",...(token?{"authorization":"Bearer "+token}:{}),...(options.headers||{})}
  });
  const raw=await response.text();
  let data={};
  try{data=raw?JSON.parse(raw):{}}catch{data={message:"Invalid GitHub response"}}
  if(!response.ok){
    const error=new Error(response.status===409||response.status===422?"A publishing update happened simultaneously; please retry.":data.message||"GitHub temporarily unavailable.");
    error.status=response.status;
    throw error;
  }
  return data;
}
function decode(file){return JSON.parse(Buffer.from(String(file.content||"").replace(/\n/g,""),"base64").toString("utf8"))}
function validJob(j){
  return !!(j&&Number.isInteger(Number(j.id))&&j.status==="active"&&
    /^jobs\/[a-z0-9][a-z0-9/_-]*\.html$/i.test(String(j.page||""))&&
    /^https:\/\//i.test(String(j.apply||""))&&
    (j.verifiedDate||j.manualLiveVerifiedAt||j.browserVerifiedAt));
}
const empty=()=>({jobId:null,status:"not_selected",selectedAt:null,postedAt:null});
async function load(base,token){
  const [jobsFile,pickFile]=await Promise.all([
    github("/contents/"+JOBS+"?ref="+encodeURIComponent(base),token),
    github("/contents/"+PICK+"?ref="+encodeURIComponent(base),token)
  ]);
  const jobs=decode(jobsFile).filter(validJob).sort((a,b)=>Number(b.id)-Number(a.id));
  const selection=decode(pickFile);
  return {jobs,selection:selection&&typeof selection==="object"?selection:empty(),sha:pickFile.sha};
}
function cleanSelection(selection,jobs){
  const job=jobs.find(j=>Number(j.id)===Number(selection?.jobId));
  return {jobId:job?Number(job.id):null,status:job?(selection.status==="posted"?"posted":"selected"):"not_selected",
    selectedAt:job?(selection.selectedAt||null):null,postedAt:job?(selection.postedAt||null):null,
    job:job||null,verification:job?(job.manualLiveVerifiedAt||job.browserVerifiedAt||job.verifiedDate||null):null};
}
export default async function handler(req,res){
  res.setHeader("Cache-Control","private, no-store");
  if(!["GET","POST"].includes(req.method)){
    res.setHeader("Allow","GET, POST");return res.status(405).json({error:"Method not allowed."});
  }
  if(!await requireAdmin(req,res))return;
  if(req.method==="POST"&&!originAllowed(req))return res.status(403).json({error:"Invalid request origin."});
  if(req.method==="POST"&&process.env.VERCEL_ENV==="preview")return res.status(403).json({error:"Preview mode is read-only. Reel selection cannot modify Production."});
  const token=process.env.GITHUB_PUBLISH_TOKEN;
  if(!token)return res.status(503).json({error:"GitHub publishing access is not configured."});
  const base=process.env.ADMIN_GITHUB_BASE||BASE;
  try{
    const {jobs,selection,sha}=await load(base,token);
    if(req.method==="GET")return res.status(200).json({
      ok:true,selection:cleanSelection(selection,jobs),
      jobs:jobs.map(j=>({id:j.id,company:j.company,role:j.role,loc:j.loc,cat:j.cat,expType:j.expType,expYears:j.expYears,
        verifiedDate:j.verifiedDate,manualLiveVerifiedAt:j.manualLiveVerifiedAt||null,apply:j.apply,page:j.page,
        logoPath:j.logoPath||null,skills:j.skills||[],elig:j.elig||j.who||"",salary:j.salary||"Not Disclosed",
        jobId:j.jobId||""}))
    });
    const action=String(req.body?.action||"");
    if(!["select","clear","mark_posted","mark_unposted"].includes(action)){
      return res.status(400).json({error:"Unsupported Reel Kit action."});
    }
    let next=empty();
    if(action==="select"){
      const id=Number(req.body?.jobId);
      if(!Number.isSafeInteger(id)||id<=0)return res.status(400).json({error:"Choose a published job."});
      const chosen=jobs.find(j=>Number(j.id)===id);
      if(!chosen)return res.status(409).json({error:"That job is not verified active in the published listings. Refresh before selecting."});
      next={jobId:id,status:"selected",selectedAt:new Date().toISOString(),postedAt:null};
    }
    if(action==="mark_posted"||action==="mark_unposted"){
      const found=jobs.find(j=>Number(j.id)===Number(selection?.jobId));
      if(!found)return res.status(409).json({error:"Selected job is no longer verified active. Choose another."});
      next={jobId:Number(found.id),status:action==="mark_posted"?"posted":"selected",
        selectedAt:selection.selectedAt||new Date().toISOString(),
        postedAt:action==="mark_posted"?new Date().toISOString():null};
    }
    const response=await github("/contents/"+PICK,token,{
      method:"PUT",
      headers:{"content-type":"application/json"},
      body:JSON.stringify({message:"Update manually selected HD Careers Instagram Reel Kit",sha,branch:base,
        content:Buffer.from(JSON.stringify(next,null,2)+"\n","utf8").toString("base64")})
    });
    return res.status(200).json({ok:true,selection:cleanSelection(next,jobs),commit:response.commit?.sha||null});
  }catch(error){
    const status=Number(error.status);
    if(status===409||status===422)return res.status(409).json({error:error.message});
    return res.status(503).json({error:"Reel Kit job data is temporarily unavailable. No selection was saved."});
  }
}
