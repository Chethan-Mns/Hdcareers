import {requireAdmin,auditMutation} from "../../lib/admin-auth.js";

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

  if(req.method!=="POST"){
    res.setHeader("Allow","POST");
    return res.status(405).json({error:"Method not allowed"});
  }

  if(!sameOrigin(req))return res.status(403).json({error:"Invalid request origin."});
  if(!await requireAdmin(req,res))return;

  if(process.env.VERCEL_ENV==="preview")return res.status(403).json({error:"Preview is read-only. Production job changes are disabled."});
  const token=process.env.GITHUB_PUBLISH_TOKEN;
  if(!token)return res.status(503).json({error:"GITHUB_PUBLISH_TOKEN is not configured in Vercel yet."});

  const submitted=Array.isArray(req.body&&req.body.jobs)?req.body.jobs:[];
  if(!submitted.length)return res.status(400).json({error:"Select at least one job to publish."});
  if(submitted.length>MAX_JOBS)return res.status(400).json({error:"Maximum "+MAX_JOBS+" jobs per deployment."});

  try{
    const incoming=submitted.map(canonicalJob);
    incoming.forEach(validateJob);

    const base=process.env.ADMIN_GITHUB_BASE||DEFAULT_BASE;
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

    const payload=JSON.stringify({event_type:"admin_publish_jobs",client_payload:{jobs:incoming}});
    if(Buffer.byteLength(payload,"utf8")>60000){
      return res.status(413).json({error:"Selected job data is too large for one deployment. Publish fewer jobs at a time."});
    }

    await auditMutation(req,"jobs.publish",incoming.map(j=>j.company+" - "+j.role).join("; ").slice(0,150));
    await github("/dispatches",token,{
      method:"POST",
      headers:{"content-type":"application/json"},
      body:payload
    });

    return res.status(202).json({
      ok:true,
      queued:true,
      count:incoming.length,
      message:"Production deployment started."
    });
  }catch(error){
    const status=Number(error&&error.status);
    const code=status===401||status===403?502:400;
    return res.status(code).json({error:(error&&error.message)||"Could not start the production deployment."});
  }
}
