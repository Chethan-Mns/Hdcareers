import crypto from "node:crypto";
import {requireAdmin} from "../../lib/admin-auth.js";

const DEFAULT_REPO = "Chethan-Mns/Hdcareers";
const DEFAULT_BASE = "main";
const MAX_JOBS = 20;
const CATS = new Set(["it","internship","apprenticeship","campus","remote","walkin","experienced","govt"]);
const CAT_FROM_LABEL = {
  "IT / Software":"it",
  "IT & Software":"it",
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

function slugify(value){
  return String(value||"job")
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[^a-z0-9]+/g,"-")
    .replace(/^-+|-+$/g,"")
    .slice(0,80)||"job";
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
  const expType=source.expType==="experienced"||source.expType==="fresher"
    ?source.expType
    :(/^0\s*years?$/i.test(expYears)||/fresher/i.test(expYears)?"fresher":"experienced");

  return {
    page:String(source.page||input.page||"").trim(),
    domain:String(source.domain||input.domain||deriveDomain(apply)).trim(),
    company,
    salary:String(input.salary||source.salary||"Not Disclosed").trim()||"Not Disclosed",
    logo:sourceLogo||[initials(company),"#0b6fe8"],
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
    apply
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
  if(!CATS.has(job.cat))errors.push("category");
  if(!["fresher","experienced"].includes(job.expType))errors.push("experience type");
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

async function deleteBranch(branch,token){
  try{
    await github("/git/refs/heads/"+encodeURIComponent(branch),token,{method:"DELETE"});
  }catch{}
}

export default async function handler(req,res){
  res.setHeader("Cache-Control","no-store");

  if(req.method!=="POST"){
    res.setHeader("Allow","POST");
    return res.status(405).json({error:"Method not allowed"});
  }

  if(!sameOrigin(req))return res.status(403).json({error:"Invalid request origin."});
  if(!requireAdmin(req,res))return;

  const token=process.env.GITHUB_PUBLISH_TOKEN;
  if(!token)return res.status(503).json({error:"GITHUB_PUBLISH_TOKEN is not configured in Vercel yet."});

  const submitted=Array.isArray(req.body&&req.body.jobs)?req.body.jobs:[];
  if(!submitted.length)return res.status(400).json({error:"Select at least one job to publish."});
  if(submitted.length>MAX_JOBS)return res.status(400).json({error:"Maximum "+MAX_JOBS+" jobs per deployment."});

  let branch="";
  let branchCreated=false;

  try{
    const incoming=submitted.map(canonicalJob);
    incoming.forEach(validateJob);

    const base=process.env.ADMIN_GITHUB_BASE||DEFAULT_BASE;
    const ref=await github("/git/ref/heads/"+encodeURIComponent(base),token);
    const baseSha=ref.object&&ref.object.sha;
    if(!baseSha)throw new Error("Could not resolve the GitHub base branch.");

    const file=await github("/contents/data/jobs.json?ref="+encodeURIComponent(base),token);
    const current=JSON.parse(Buffer.from(String(file.content||"").replace(/\n/g,""),"base64").toString("utf8"));
    if(!Array.isArray(current))throw new Error("data/jobs.json is not a JSON array.");

    const existingUrls=new Set(current.map(j=>normalizeUrl(j.apply)));
    const existingPages=new Set(current.map(j=>String(j.page||"").toLowerCase()));
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

    if(duplicates.length){
      return res.status(409).json({error:"Duplicate job detected.",duplicates});
    }

    let nextId=current.reduce((max,j)=>Math.max(max,Number(j.id)||0),0)+1;
    for(const job of incoming){
      job.id=nextId++;
      let basePage=job.page&&job.page.startsWith("jobs/")&&job.page.endsWith(".html")
        ?job.page
        :"jobs/"+slugify(job.company+"-"+job.role)+".html";
      let page=basePage;
      let n=2;
      while(existingPages.has(page.toLowerCase())){
        page=basePage.replace(/\.html$/,"-"+n+".html");
        n++;
      }
      job.page=page;
      existingPages.add(page.toLowerCase());
    }

    const updated=[...incoming,...current];
    const stamp=new Date().toISOString().replace(/[-:TZ.]/g,"").slice(0,14);
    branch="admin-jobs-"+stamp+"-"+crypto.randomBytes(3).toString("hex");

    await github("/git/refs",token,{
      method:"POST",
      headers:{"content-type":"application/json"},
      body:JSON.stringify({ref:"refs/heads/"+branch,sha:baseSha})
    });
    branchCreated=true;

    await github("/contents/data/jobs.json",token,{
      method:"PUT",
      headers:{"content-type":"application/json"},
      body:JSON.stringify({
        message:"Add "+incoming.length+" job"+(incoming.length===1?"":"s")+" from admin",
        content:Buffer.from(JSON.stringify(updated,null,2)+"\n","utf8").toString("base64"),
        sha:file.sha,
        branch
      })
    });

    const lines=incoming.map(j=>"- "+j.company+" — "+j.role+" ("+j.loc+")").join("\n");
    const pr=await github("/pulls",token,{
      method:"POST",
      headers:{"content-type":"application/json"},
      body:JSON.stringify({
        title:"Publish "+incoming.length+" job"+(incoming.length===1?"":"s")+" from HD Careers Admin",
        head:branch,
        base,
        body:"Created from the authenticated HD Careers admin.\n\nJobs:\n"+lines+"\n\nThe Admin Job Generator workflow will run generate.py on this branch and update the homepage plus individual job pages. Review the Vercel preview before merging."
      })
    });

    return res.status(200).json({
      ok:true,
      branch,
      prNumber:pr.number,
      prUrl:pr.html_url,
      jobs:incoming.map(j=>({id:j.id,company:j.company,role:j.role,page:j.page}))
    });
  }catch(error){
    if(branchCreated&&branch)await deleteBranch(branch,token);
    const status=Number(error&&error.status);
    const code=status===401||status===403?502:400;
    return res.status(code).json({error:(error&&error.message)||"Could not create the publishing pull request."});
  }
}
