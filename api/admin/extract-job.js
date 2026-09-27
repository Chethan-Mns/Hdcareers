import {requireAdmin} from "../../lib/admin-auth.js";
import dns from "node:dns/promises";
import crypto from "node:crypto";
import net from "node:net";

const MAX_BYTES = 2_000_000;
const MAX_REDIRECTS = 3;
const TIMEOUT_MS = 9000;

function normalizeKnownCareerUrl(input){
  const u=new URL(input);
  const host=u.hostname.toLowerCase();

  if((host==="pwc.in"||host.endsWith(".pwc.in"))&&u.pathname.includes("/careers/experienced-jobs/description.html")){
    const reqId=(u.searchParams.get("wdjobreqid")||"").trim();
    const site=(u.searchParams.get("wdjobsite")||"Global_Experienced_Careers").trim();
    const rawTitle=(u.searchParams.get("jobtitle")||"").trim();
    const parts=rawTitle.split("|").map(x=>x.trim()).filter(Boolean);
    const role=parts[0]||"";
    const location=parts.slice(1).join(" / ");
    if(reqId){
      const workdayTitle=slugify(rawTitle||role||reqId);
      const workdayUrl="https://pwc.wd3.myworkdayjobs.com/en-US/"+encodeURIComponent(site)+"/job/"+workdayTitle+"_"+encodeURIComponent(reqId);
      return {
        fetchUrl:workdayUrl,
        applyUrl:workdayUrl,
        companyHint:"PwC",
        roleHint:role,
        locationHint:location,
        domainHint:"pwc.com",
        allowPartial:true
      };
    }
  }

  return {fetchUrl:u.href,applyUrl:u.href,companyHint:"",roleHint:"",locationHint:"",domainHint:"",allowPartial:false};
}

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

function collectNextData(html){
  const m=html.match(/<script[^>]*id\s*=\s*["']__NEXT_DATA__["'][^>]*>([\s\S]*?)<\/script>/i);
  if(!m)return null;
  try{return JSON.parse(m[1].trim());}catch{return null;}
}

function walkObjects(value,out=[]){
  if(!value||typeof value!=="object")return out;
  if(Array.isArray(value)){
    for(const x of value)walkObjects(x,out);
    return out;
  }
  out.push(value);
  for(const v of Object.values(value))walkObjects(v,out);
  return out;
}

function normKey(k){
  return String(k||"").toLowerCase().replace(/[^a-z0-9]/g,"");
}

function deepField(obj,names){
  const wanted=new Set(names.map(normKey));
  const seen=new Set();
  function visit(v){
    if(!v||typeof v!=="object"||seen.has(v))return "";
    seen.add(v);
    if(!Array.isArray(v)){
      for(const [k,val] of Object.entries(v)){
        if(wanted.has(normKey(k))){
          const t=textValue(val);
          if(t)return t;
        }
      }
      for(const val of Object.values(v)){
        const hit=visit(val);
        if(hit)return hit;
      }
    }else{
      for(const val of v){
        const hit=visit(val);
        if(hit)return hit;
      }
    }
    return "";
  }
  return visit(obj);
}

function findNextJobObject(nextData,jobId){
  if(!nextData)return null;
  const id=String(jobId||"").trim();
  let best=null;
  let bestScore=0;
  for(const obj of walkObjects(nextData,[])){
    let score=0;
    for(const [k,v] of Object.entries(obj)){
      const nk=normKey(k);
      const tv=textValue(v);
      if(id&&tv===id){
        score+=/jobid|requisitionid|reqid|jobnumber/.test(nk)?30:12;
      }
      if(/jobtitle|positiontitle|title/.test(nk)&&tv)score+=4;
      if(/jobdescription|description/.test(nk)&&tv)score+=4;
      if(/location|city|country/.test(nk)&&tv)score+=2;
      if(/qualification|responsibil|requirement/.test(nk)&&tv)score+=2;
    }
    if(score>bestScore){bestScore=score;best=obj;}
  }
  return bestScore>=10?best:null;
}

function ibmFallback(nextData,input){
  let u;
  try{u=new URL(input);}catch{return null;}
  const host=u.hostname.toLowerCase();
  if(host!=="careers.ibm.com")return null;
  const pathParts=u.pathname.split("/").filter(Boolean);
  const queryId=(u.searchParams.get("jobId")||"").trim();
  const pathId=(pathParts[pathParts.length-1]||"").match(/^\d+$/)?.[0]||"";
  const jobId=queryId||pathId;
  if(!jobId)return null;

  const obj=findNextJobObject(nextData,jobId);
  if(!obj)return {
    jobId,
    company:"IBM",
    title:pathId&&pathParts.length>=2?decodeURIComponent(pathParts[pathParts.length-2]).replace(/-/g," "):"",
    description:"",
    location:"",
    eligibility:"",
    responsibilities:[],
    posted:""
  };

  const title=deepField(obj,["jobTitle","positionTitle","title","jobName"]);
  const description=deepField(obj,["jobDescription","description","jobDesc","descriptionHtml"]);
  const location=deepField(obj,["primaryLocation","jobLocation","location","locations","city"]);
  const eligibility=deepField(obj,["qualifications","requiredQualifications","minimumQualifications","educationRequirements","requirements"]);
  const responsibilityText=deepField(obj,["responsibilities","jobResponsibilities","duties"]);
  const posted=deepField(obj,["datePosted","postedDate","postingDate","createdDate"]);

  return {
    jobId,
    company:"IBM",
    title,
    description,
    location,
    eligibility,
    responsibilities:splitResponsibilities(responsibilityText||description),
    posted
  };
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

function sentenceList(s){
  return stripHtml(s)
    .replace(/\s+/g," ")
    .split(/(?<=[.!?])\s+(?=[A-Z0-9])/)
    .map(x=>x.trim())
    .filter(Boolean);
}

function uniqueText(items){
  const seen=new Set();
  const out=[];
  for(const item of items){
    const clean=String(item||"").replace(/\s+/g," ").replace(/^[-–—*•\d.)\s]+/,"").trim();
    if(!clean)continue;
    const key=clean.toLowerCase().replace(/[^a-z0-9]+/g," ").trim();
    if(!key||seen.has(key))continue;
    seen.add(key);
    out.push(clean);
  }
  return out;
}

function sectionText(text,headings){
  const src=stripHtml(text);
  if(!src)return "";
  const escaped=headings.map(x=>x.replace(/[.*+?^$\{\}()|[\]\\]/g,"\\function splitResponsibilities(s){
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
")).join("|");
  const re=new RegExp("(?:^|\\n|\\.\\s+)("+escaped+")\\s*:?\\s*","i");
  const m=re.exec(src);
  if(!m)return "";
  const after=src.slice(m.index+m[0].length);
  const stop=after.search(/(?:\n|\.\s+)(?:qualifications?|requirements?|skills?|education|experience|about us|what we do|preferred|mandatory|benefits?|how to apply)\s*:?/i);
  return (stop>=0?after.slice(0,stop):after).trim();
}

function splitResponsibilities(s){
  const text=stripHtml(s);
  if(!text)return [];

  const focused=sectionText(text,[
    "key job responsibilities",
    "job responsibilities",
    "responsibilities",
    "what you will do",
    "what you'll do",
    "your role",
    "duties"
  ]);

  const source=focused||text;
  let candidates=source
    .split(/\n|•|\u2022|;(?=\s+[A-Z])|(?<=[.!?])\s+(?=(?:Work|Develop|Design|Build|Create|Support|Collaborate|Execute|Prepare|Maintain|Analyze|Validate|Test|Assist|Manage|Deliver|Drive|Perform|Monitor|Ensure|Use|Translate|Document|Identify|Implement|Review|Coordinate|Troubleshoot|Participate|Contribute)\b)/i)
    .map(x=>x.replace(/^[-–—*\d.)\s]+/,"").trim())
    .filter(x=>x.length>=20&&x.length<=260);

  const action=/^(Work|Develop|Design|Build|Create|Support|Collaborate|Execute|Prepare|Maintain|Analyze|Validate|Test|Assist|Manage|Deliver|Drive|Perform|Monitor|Ensure|Use|Translate|Document|Identify|Implement|Review|Coordinate|Troubleshoot|Participate|Contribute)\b/i;
  const actionItems=candidates.filter(x=>action.test(x));

  if(actionItems.length>=3)candidates=actionItems;
  return uniqueText(candidates).slice(0,6);
}

function cleanDescription(s){
  const x=stripHtml(s);
  if(!x)return "";

  const beforeResponsibilities=x.split(/(?:\n|\.\s+)(?:key job responsibilities|job responsibilities|responsibilities|what you will do|what you'll do)\s*:?/i)[0].trim();
  const source=beforeResponsibilities||x;
  const boilerplate=/^(about us|who we are|our purpose|our people|deloitte refers to|privacy|equal opportunity|accommodation|recruiting tips)/i;
  const sentences=sentenceList(source)
    .filter(x=>x.length>=35)
    .filter(x=>!boilerplate.test(x))
    .filter(x=>!/^(job description|description|position summary)\s*:?$/i.test(x));

  let picked=[];
  let total=0;
  for(const sentence of uniqueText(sentences)){
    if(picked.length>=3)break;
    if(total+sentence.length>520&&picked.length>=2)break;
    picked.push(sentence);
    total+=sentence.length;
  }

  let summary=(picked.length?picked.join(" "):source).trim();
  if(summary.length>560){
    summary=summary.slice(0,560).replace(/\s+\S*$/,"").replace(/[,:;\-]+$/,"").trim();
  }
  if(summary&&!/[.!?]$/.test(summary))summary+=".";
  return summary;
}

function cleanEligibility(raw,descriptionSource){
  const text=stripHtml(raw);
  const source=text||stripHtml(descriptionSource);
  if(!source)return "";

  const signals=/(bachelor|master|degree|b\.e\.?|b\.tech|m\.tech|mba|graduate|qualification|minimum|at least|years? of experience|experience required|required skill|must have|preferred|proficien|knowledge of|familiarity with|sql|python|java|testing|analytics)/i;
  const sentences=sentenceList(source);
  const relevant=uniqueText(sentences.filter(x=>signals.test(x)&&x.length>=25&&x.length<=260));

  if(relevant.length){
    return relevant.slice(0,4).join(" ").slice(0,620);
  }

  if(text&&text.length<=420)return text;
  return "";
}

function labeledValue(text,label){
  const re=new RegExp(label+"\\s*[:\\-]\\s*([^\\n]{2,180})","i");
  const m=String(text||"").match(re);
  return m?m[1].replace(/\\s+/g," ").trim():"";
}

function pwcResponsibilities(text){
  const src=String(text||"");
  const out=[];
  const re=/\([a-l]\)\s+([\s\S]*?)(?=\([a-l]\)\s+|Mandatory skill sets|Preferred skill sets|Year of experience|Qualifications\s*[-:]|$)/gi;
  let m;
  while((m=re.exec(src))&&out.length<6){
    const item=m[1].replace(/\s+/g," ").trim();
    if(item.length>=20&&item.length<=320)out.push(item);
  }
  return out;
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

    const hint=normalizeKnownCareerUrl(input);
    let page;
    try{
      page=await fetchHtml(hint.fetchUrl);
    }catch(error){
      if(!hint.allowPartial)throw error;
      page={html:"",url:hint.applyUrl};
    }
    const jsonLd=collectJsonLd(page.html);
    let job=null;
    for(const item of jsonLd){job=findJobPosting(item);if(job)break;}
    const nextData=collectNextData(page.html);
    const ibm=ibmFallback(nextData,input);

    const pageText=stripHtml(page.html);
    const fallbackTitle=meta(page.html,null,"og:title")||titleTag(page.html);
    const fallbackDesc=meta(page.html,"description")||meta(page.html,null,"og:description");
    const title=textValue(job&&job.title)||(ibm&&ibm.title)||hint.roleHint||fallbackTitle.replace(/\s*[-|–].*$/,"").trim();
    const company=getCompany(job)||(ibm&&ibm.company)||hint.companyHint||meta(page.html,null,"og:site_name")||"";
    const workdayDescription=(hint.companyHint==="PwC"&&pageText)?pageText:"";
    const rawDescription=(job&&job.description)||(ibm&&ibm.description)||fallbackDesc||workdayDescription;
    const description=cleanDescription(rawDescription);
    let responsibilities=(ibm&&ibm.responsibilities&&ibm.responsibilities.length)?ibm.responsibilities:splitResponsibilities((job&&job.responsibilities)||(job&&job.description)||rawDescription||"");
    if(!responsibilities.length&&hint.companyHint==="PwC")responsibilities=pwcResponsibilities(pageText);
    const location=getLocation(job)||(ibm&&ibm.location)||hint.locationHint||labeledValue(pageText,"Job Location");
    const salary=getSalary(job)||"Not Disclosed";
    const domain=hint.domainHint||new URL(page.url).hostname.replace(/^www\./,"");
    const exp=detectExperience(job,[description,labeledValue(pageText,"Experience"),labeledValue(pageText,"Year of experience required")].filter(Boolean).join(" "));
    const category=inferCategory(title,description,domain,exp);
    const rawEligibility=textValue(job&&job.qualifications)||textValue(job&&job.educationRequirements)||textValue(job&&job.experienceRequirements)||(ibm&&ibm.eligibility)||labeledValue(pageText,"Qualifications")||"";
    const eligibility=cleanEligibility(rawEligibility,rawDescription);
    const posted=textValue(job&&job.datePosted)||(ibm&&ibm.posted)||"";
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
      apply:hint.applyUrl||page.url,
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
