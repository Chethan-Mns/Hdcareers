import {requireAdmin} from "../../lib/admin-auth.js";
import dns from "node:dns/promises";
import crypto from "node:crypto";
import net from "node:net";

const MAX_BYTES = 2_000_000;
const MAX_REDIRECTS = 3;
const TIMEOUT_MS = 9000;

function isPrivateIp(ip){
  if(net.isIP(ip)===4){
    const p=ip.split(".").map(Number);
    return p[0]===10 ||
      p[0]===127 ||
      (p[0]===169&&p[1]===254) ||
      (p[0]===172&&p[1]>=16&&p[1]<=31) ||
      (p[0]===192&&p[1]===168) ||
      p[0]===0;
  }
  if(net.isIP(ip)===6){
    const x=ip.toLowerCase();
    return x==="::1" || x==="::" || x.startsWith("fc") || x.startsWith("fd") || x.startsWith("fe80:");
  }
  return false;
}

async function assertPublicUrl(input){
  let u;
  try{u=new URL(input)}catch{throw new Error("Enter a valid job URL.");}
  if(u.protocol!=="https:")throw new Error("Only HTTPS job links are allowed.");
  const host=u.hostname.toLowerCase();
  if(host==="localhost"||host.endsWith(".local")||host.endsWith(".internal"))throw new Error("Private hostnames are not allowed.");
  if(net.isIP(host)&&isPrivateIp(host))throw new Error("Private IP addresses are not allowed.");
  const answers=await dns.lookup(host,{all:true,verbatim:true});
  if(!answers.length)throw new Error("Could not resolve the job website.");
  if(answers.some(x=>isPrivateIp(x.address)))throw new Error("Private network destinations are not allowed.");
  return u;
}

async function fetchHtml(input){
  let current=await assertPublicUrl(input);
  for(let i=0;i<=MAX_REDIRECTS;i++){
    const controller=new AbortController();
    const timer=setTimeout(()=>controller.abort(),TIMEOUT_MS);
    let response;
    try{
      response=await fetch(current,{
        redirect:"manual",
        signal:controller.signal,
        headers:{
          "user-agent":"Mozilla/5.0 (compatible; HD-Careers-Admin/1.0)",
          "accept":"text/html,application/xhtml+xml"
        }
      });
    }finally{
      clearTimeout(timer);
    }
    if([301,302,303,307,308].includes(response.status)){
      const location=response.headers.get("location");
      if(!location)throw new Error("The job page redirected without a destination.");
      current=await assertPublicUrl(new URL(location,current).href);
      continue;
    }
    if(!response.ok)throw new Error("Job page returned HTTP "+response.status+".");
    const type=(response.headers.get("content-type")||"").toLowerCase();
    if(!type.includes("text/html")&&!type.includes("application/xhtml+xml"))throw new Error("The supplied link is not an HTML job page.");
    const len=Number(response.headers.get("content-length")||0);
    if(len>MAX_BYTES)throw new Error("Job page is too large to process.");
    const reader=response.body.getReader();
    const chunks=[];
    let total=0;
    while(true){
      const part=await reader.read();
      if(part.done)break;
      total+=part.value.byteLength;
      if(total>MAX_BYTES)throw new Error("Job page is too large to process.");
      chunks.push(part.value);
    }
    const bytes=new Uint8Array(total);
    let offset=0;
    for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}
    return {html:new TextDecoder().decode(bytes),url:current.href};
  }
  throw new Error("Too many redirects.");
}

function decodeEntities(s){
  return String(s||"")
    .replace(/&nbsp;/gi," ")
    .replace(/&amp;/gi,"&")
    .replace(/&quot;/gi,'"')
    .replace(/&#39;|&apos;/gi,"'")
    .replace(/&lt;/gi,"<")
    .replace(/&gt;/gi,">")
    .replace(/&#(\d+);/g,(_,n)=>String.fromCharCode(Number(n)));
}

function stripHtml(s){
  return decodeEntities(String(s||"")
    .replace(/<script[\s\S]*?<\/script>/gi," ")
    .replace(/<style[\s\S]*?<\/style>/gi," ")
    .replace(/<br\s*\/?\s*>/gi,"\n")
    .replace(/<\/p>|<\/li>|<\/div>|<\/h\d>/gi,"\n")
    .replace(/<[^>]+>/g," "))
    .replace(/[ \t]+/g," ")
    .replace(/\n\s*\n+/g,"\n")
    .trim();
}

function meta(html,name,property){
  const tags=html.match(/<meta\b[^>]*>/gi)||[];
  for(const tag of tags){
    const n=(tag.match(/\bname\s*=\s*["']([^"']+)["']/i)||[])[1];
    const p=(tag.match(/\bproperty\s*=\s*["']([^"']+)["']/i)||[])[1];
    if((name&&n&&n.toLowerCase()===name.toLowerCase())||(property&&p&&p.toLowerCase()===property.toLowerCase())){
      return decodeEntities((tag.match(/\bcontent\s*=\s*["']([^"']*)["']/i)||[])[1]||"");
    }
  }
  return "";
}

function titleTag(html){
  return decodeEntities((html.match(/<title[^>]*>([\s\S]*?)<\/title>/i)||[])[1]||"").replace(/\s+/g," ").trim();
}

function collectJsonLd(html){
  const out=[];
  const re=/<script[^>]+type\s*=\s*["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
  let m;
  while((m=re.exec(html))){
    try{
      const data=JSON.parse(m[1].trim());
      out.push(data);
    }catch{}
  }
  return out;
}

function findJobPosting(value){
  if(!value)return null;
  if(Array.isArray(value)){
    for(const x of value){const hit=findJobPosting(x);if(hit)return hit;}
    return null;
  }
  if(typeof value!=="object")return null;
  const t=value["@type"];
  const types=Array.isArray(t)?t:[t];
  if(types.filter(Boolean).some(x=>String(x).toLowerCase()==="jobposting"))return value;
  if(value["@graph"]){const hit=findJobPosting(value["@graph"]);if(hit)return hit;}
  for(const v of Object.values(value)){
    if(v&&typeof v==="object"){const hit=findJobPosting(v);if(hit)return hit;}
  }
  return null;
}

function textValue(v){
  if(v==null)return "";
  if(typeof v==="string"||typeof v==="number")return String(v);
  if(Array.isArray(v))return v.map(textValue).filter(Boolean).join(", ");
  if(typeof v==="object")return textValue(v.name||v.value||v.text||"");
  return "";
}

function getCompany(j){
  return textValue(j&&j.hiringOrganization&&j.hiringOrganization.name)||"";
}

function getLocation(j){
  if(!j)return "";
  if(String(j.jobLocationType||"").toUpperCase().includes("TELECOMMUTE"))return "Remote";
  const locs=Array.isArray(j.jobLocation)?j.jobLocation:[j.jobLocation];
  const values=[];
  for(const loc of locs.filter(Boolean)){
    const a=loc.address||loc;
    const parts=[a.addressLocality,a.addressRegion,a.addressCountry&&((a.addressCountry.name)||a.addressCountry)].map(textValue).filter(Boolean);
    const one=[...new Set(parts)].join(", ");
    if(one)values.push(one);
  }
  if(values.length)return [...new Set(values)].join(" / ");
  return textValue(j.applicantLocationRequirements);
}

function getSalary(j){
  const b=j&&j.baseSalary;
  if(!b)return "";
  const currency=textValue(b.currency);
  const v=b.value||b;
  if(typeof v==="object"){
    const min=textValue(v.minValue);
    const max=textValue(v.maxValue);
    const unit=textValue(v.unitText);
    let amount=min&&max?min+" - "+max:(min||max||textValue(v.value));
    if(amount)return [currency,amount,unit].filter(Boolean).join(" ");
  }
  const raw=textValue(v);
  return [currency,raw].filter(Boolean).join(" ");
}

function slugify(s){
  return String(s||"job").toLowerCase().normalize("NFKD").replace(/[^a-z0-9]+/g,"-").replace(/^-+|-+$/g,"").slice(0,80)||"job";
}

function initials(company){
  const parts=String(company||"Company").split(/\s+/).filter(Boolean);
  if(parts.length===1)return parts[0].slice(0,2).toUpperCase();
  return (parts[0][0]+parts[1][0]).toUpperCase();
}

function detectExperience(j,desc){
  const raw=[textValue(j&&j.experienceRequirements),desc].join(" ");
  let m=raw.match(/(?:minimum\s+of\s+|at\s+least\s+)?(\d+)\s*(?:\+|plus)?\s*(?:-|to)?\s*(\d+)?\s*years?\s+(?:of\s+)?experience/i);
  if(!m)m=raw.match(/(\d+)\s*(?:-|to)\s*(\d+)\s*years?/i);
  if(!m)return {type:"fresher",years:"0 years"};
  const a=Number(m[1]);
  const b=m[2]?Number(m[2]):null;
  return {type:a>0?"experienced":"fresher",years:b?a+"-"+b+" years":a+"+ years"};
}

function inferCategory(title,desc,domain,exp){
  const x=(title+" "+desc).toLowerCase();
  if(x.includes("internship")||/\bintern\b/.test(x))return "internship";
  if(x.includes("apprentice"))return "apprenticeship";
  if(x.includes("walk-in")||x.includes("walk in"))return "walkin";
  if(x.includes("remote")||x.includes("work from home"))return "remote";
  if(domain.endsWith(".gov.in")||domain.includes("government"))return "govt";
  if(exp.type==="experienced")return "experienced";
  return "it";
}

function splitResponsibilities(s){
  const text=stripHtml(s);
  if(!text)return [];
  const candidates=text.split(/\n|•|\u2022|;(?=\s+[A-Z])/).map(x=>x.replace(/^[-–—*\d.)\s]+/,"").trim()).filter(x=>x.length>=20&&x.length<=220);
  return [...new Set(candidates)].slice(0,6);
}

function cleanDescription(s){
  const x=stripHtml(s);
  if(!x)return "";
  return x.split(/\n+/).map(v=>v.trim()).filter(Boolean).slice(0,5).join(" ").slice(0,900);
}

export default async function handler(req,res){
  if(req.method!=="POST"){
    res.setHeader("Allow","POST");
    return res.status(405).json({error:"Method not allowed"});
  }

  res.setHeader("Cache-Control","no-store");
  if(!requireAdmin(req,res))return;

  try{
    const input=req.body&&req.body.url;
    if(!input)return res.status(400).json({error:"Job URL is required."});

    const page=await fetchHtml(input);
    const jsonLd=collectJsonLd(page.html);
    let job=null;
    for(const item of jsonLd){job=findJobPosting(item);if(job)break;}

    const fallbackTitle=meta(page.html,null,"og:title")||titleTag(page.html);
    const fallbackDesc=meta(page.html,"description")||meta(page.html,null,"og:description");
    const title=textValue(job&&job.title)||fallbackTitle.replace(/\s*[-|–].*$/,"").trim();
    const company=getCompany(job)||meta(page.html,null,"og:site_name")||"";
    const description=cleanDescription((job&&job.description)||fallbackDesc);
    const responsibilities=splitResponsibilities((job&&job.responsibilities)||(job&&job.description)||"");
    const location=getLocation(job);
    const salary=getSalary(job)||"Not Disclosed";
    const domain=new URL(page.url).hostname.replace(/^www\./,"");
    const exp=detectExperience(job,description);
    const category=inferCategory(title,description,domain,exp);
    const eligibility=stripHtml(textValue(job&&job.qualifications)||textValue(job&&job.educationRequirements)||textValue(job&&job.experienceRequirements)||"");
    const posted=textValue(job&&job.datePosted);
    const date=posted?new Date(posted):new Date();
    const safeDate=Number.isNaN(date.getTime())?new Date():date;
    const formatted=safeDate.toLocaleDateString("en-GB",{day:"2-digit",month:"short",year:"numeric"}).replace(/^0/,"");

    const data={
      sourceUrl:page.url,
      domain,
      company,
      role:title,
      roleTag:title,
      loc:location||"Not Specified",
      locationFilter:location||"",
      salary,
      batch:"Not Specified",
      elig:eligibility||"Review the official job posting for detailed eligibility requirements.",
      cat:category,
      expType:exp.type,
      expYears:exp.years,
      date:formatted,
      desc:description||("Review the official "+(company||"company")+" job posting for role details."),
      resp:responsibilities.length?responsibilities:["Review the official job description and responsibilities before applying."],
      apply:page.url,
      page:"jobs/"+slugify((company||domain)+"-"+(title||"job"))+".html",
      logo:[initials(company||domain),"#0b6fe8"],
      extraction:{
        structuredJobPosting:Boolean(job),
        title:Boolean(title),
        company:Boolean(company),
        location:Boolean(location),
        salary:salary!=="Not Disclosed",
        eligibility:Boolean(eligibility)
      }
    };

    return res.status(200).json({ok:true,data});
  }catch(error){
    const msg=error&&error.name==="AbortError"?"The job page took too long to respond.":(error&&error.message)||"Could not extract the job page.";
    return res.status(400).json({error:msg});
  }
}
