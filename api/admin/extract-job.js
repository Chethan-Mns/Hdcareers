import {requireAdmin} from "../../lib/admin-auth.js";
import dns from "node:dns/promises";
import net from "node:net";

export const config={maxDuration:30};

const MAX_BYTES=3_500_000;
const MAX_READER_BYTES=2_500_000;
const MAX_REDIRECTS=4;
const TIMEOUT_MS=6500;
const READER_TIMEOUT_MS=12000;

const COMPANY_HOST_HINTS=[
["deloitte","Deloitte"],["ibm","IBM"],["accenture","Accenture"],["pwc","PwC"],
["infosys","Infosys"],["tcs","TCS"],["wipro","Wipro"],["cognizant","Cognizant"],
["capgemini","Capgemini"],["microsoft","Microsoft"],["google","Google"],["amazon","Amazon"],
["apple","Apple"],["oracle","Oracle"],["salesforce","Salesforce"],["adobe","Adobe"],
["servicenow","ServiceNow"],["qualcomm","Qualcomm"],["intel","Intel"],["nvidia","NVIDIA"],
["jpmorgan","JPMorgan Chase"],["jpmc","JPMorgan Chase"],["goldmansachs","Goldman Sachs"],
["kpmg","KPMG"],["ltimindtree","LTIMindtree"],["hcltech","HCLTech"],["techmahindra","Tech Mahindra"],
["zoho","Zoho"],["flipkart","Flipkart"],["paypal","PayPal"]
];
const ATS_HOSTS=["myworkdayjobs.com","workdayjobs.com","oraclecloud.com","greenhouse.io","lever.co","smartrecruiters.com","icims.com","taleo.net","successfactors.com","phenompeople.com"];
const INDIA_CITIES=["hyderabad","bengaluru","bangalore","chennai","pune","mumbai","noida","gurugram","gurgaon","delhi","new delhi","kolkata","kochi","cochin","ahmedabad","jaipur","indore","coimbatore","trivandrum","thiruvananthapuram","bhubaneswar","mysuru","mysore","remote"];
const ACTION_VERBS="Work|Develop|Design|Build|Create|Support|Collaborate|Execute|Prepare|Maintain|Analyze|Validate|Test|Assist|Manage|Deliver|Drive|Perform|Monitor|Ensure|Use|Translate|Document|Identify|Implement|Review|Coordinate|Troubleshoot|Participate|Contribute|Own|Lead|Configure|Automate|Debug|Deploy|Integrate|Optimize|Partner|Communicate|Research|Assess|Plan";

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

async function fetchReader(input){
  const u=await assertPublicUrl(input);
  const controller=new AbortController();
  const timer=setTimeout(()=>controller.abort(),READER_TIMEOUT_MS);
  try{
    const headers={"accept":"application/json","x-return-format":"markdown","x-engine":"browser","user-agent":"HD-Careers-Admin/2.0"};
    if(process.env.JINA_API_KEY)headers.authorization="Bearer "+process.env.JINA_API_KEY;
    const response=await fetch("https://r.jina.ai/"+u.href,{signal:controller.signal,headers});
    if(!response.ok)throw new Error("Reader fallback returned HTTP "+response.status+".");
    const raw=await readReaderBody(response);
    try{
      const body=JSON.parse(raw);
      const data=body.data||body;
      return {content:String(data.content||data.markdown||""),title:String(data.title||""),url:String(data.url||u.href)};
    }catch{
      return {content:raw,title:"",url:u.href};
    }
  }finally{
    clearTimeout(timer);
  }
}

async function readReaderBody(response){
  const reader=response.body&&response.body.getReader?response.body.getReader():null;
  if(!reader)return await response.text();
  const chunks=[];let total=0;
  while(true){
    const part=await reader.read();
    if(part.done)break;
    total+=part.value.byteLength;
    if(total>MAX_READER_BYTES)throw new Error("Rendered job page is too large to process.");
    chunks.push(part.value);
  }
  const bytes=new Uint8Array(total);let offset=0;
  for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}
  return new TextDecoder().decode(bytes);
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

function absoluteHttpUrl(value,base){
  try{
    const u=new URL(String(value||""),base);
    return /^https?:$/.test(u.protocol)?u.href:"";
  }catch{return "";}
}

function logoValue(value,base){
  if(!value)return "";
  if(typeof value==="string")return absoluteHttpUrl(value,base);
  if(Array.isArray(value)){
    for(const item of value){
      const hit=logoValue(item,base);
      if(hit)return hit;
    }
    return "";
  }
  if(typeof value==="object"){
    for(const key of ["url","contentUrl","@id","src"]){
      const hit=absoluteHttpUrl(value[key],base);
      if(hit)return hit;
    }
  }
  return "";
}

function documentIcon(html,base){
  const links=String(html||"").match(/<link\b[^>]*>/gi)||[];
  const ranked=[];
  for(const tag of links){
    const rel=(tag.match(/\brel\s*=\s*["']([^"']+)["']/i)||[])[1]||"";
    const href=(tag.match(/\bhref\s*=\s*["']([^"']+)["']/i)||[])[1]||"";
    if(!href||!/(?:apple-touch-icon|icon)/i.test(rel))continue;
    const url=absoluteHttpUrl(decodeEntities(href),base);
    if(!url)continue;
    const score=/apple-touch-icon/i.test(rel)?3:/icon/i.test(rel)?2:1;
    ranked.push({url,score});
  }
  ranked.sort((a,b)=>b.score-a.score);
  return ranked[0]?.url||"";
}

function organizationLogo(jsonRoots,structured,company,html,base){
  const direct=[
    structured&&structured.hiringOrganization&&structured.hiringOrganization.logo,
    structured&&structured.hiringOrganization&&structured.hiringOrganization.image,
    structured&&structured.logo,
    structured&&structured.image
  ];
  for(const value of direct){
    const hit=logoValue(value,base);
    if(hit)return hit;
  }

  const companyKey=normalizeSpace(company).toLowerCase();
  let organizationSite="";
  const directOrg=structured&&structured.hiringOrganization;
  if(directOrg){
    organizationSite=logoValue(directOrg.url,base)||logoValue(directOrg.sameAs,base);
  }

  for(const root of jsonRoots){
    for(const obj of walkObjects(root,[])){
      const types=Array.isArray(obj&&obj["@type"])?obj["@type"]:[obj&&obj["@type"]];
      if(!types.some(x=>/organization/i.test(String(x||""))))continue;
      const name=normalizeSpace(textValue(obj&&obj.name)).toLowerCase();
      if(companyKey&&name&&name!==companyKey&&!name.includes(companyKey)&&!companyKey.includes(name))continue;
      const hit=logoValue(obj&&obj.logo,base)||logoValue(obj&&obj.image,base);
      if(hit)return hit;
      if(!organizationSite){
        organizationSite=logoValue(obj&&obj.url,base)||logoValue(obj&&obj.sameAs,base);
      }
    }
  }

  if(organizationSite){
    try{
      const host=new URL(organizationSite).hostname.replace(/^www\./,"");
      if(host){
        return "https://www.google.com/s2/favicons?domain_url="+encodeURIComponent("https://"+host)+"&sz=128";
      }
    }catch{}
  }

  const icon=documentIcon(html,base);
  if(icon)return icon;

  const og=absoluteHttpUrl(meta(html,null,"og:image"),base);
  return /(?:logo|brand|icon|favicon)/i.test(og)?og:"";
}


function headingOne(html){
  return stripHtml((String(html||"").match(/<h1\b[^>]*>([\s\S]*?)<\/h1>/i)||[])[1]||"").replace(/\s+/g," ").trim();
}

function formatDate(value){
  const raw=normalizeSpace(value);
  let date=raw?new Date(raw):new Date();
  if(Number.isNaN(date.getTime())){
    const iso=raw.match(/\b(20\d{2})[-\/.](\d{1,2})[-\/.](\d{1,2})\b/);
    const dmy=raw.match(/\b(\d{1,2})[-\/.](\d{1,2})[-\/.](20\d{2})\b/);
    if(iso)date=new Date(Number(iso[1]),Number(iso[2])-1,Number(iso[3]));
    else if(dmy)date=new Date(Number(dmy[3]),Number(dmy[2])-1,Number(dmy[1]));
    else date=new Date();
  }
  return date.toLocaleDateString("en-GB",{day:"2-digit",month:"short",year:"numeric"}).replace(/^0/,"");
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


function collectEmbeddedJson(html){
  const out=[];
  const re=/<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
  let m;
  while((m=re.exec(String(html||"")))&&out.length<40){
    const attrs=m[1]||"";
    const body=m[2].trim();
    if(!body||body.length>1500000)continue;
    if(/application\/(?:ld\+)?json|__NEXT_DATA__|__APOLLO_STATE__|application\/json/i.test(attrs)){
      try{out.push(JSON.parse(body));}catch{}
    }
  }
  return out;
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


function normalizeSpace(s){return String(s||"").replace(/\s+/g," ").trim();}
function escapeRegExp(s){return String(s||"").replace(/[.*+?^$\{\}()|[\]\\]/g,"\\$&");}
function titleCase(s){return normalizeSpace(s).split(" ").map(w=>/^[A-Z0-9]{2,}$/.test(w)?w:(w?w[0].toUpperCase()+w.slice(1).toLowerCase():w)).join(" ");}

function sentenceList(s){
  return stripHtml(s).replace(/\s+/g," ").split(/(?<=[.!?])\s+(?=[A-Z0-9])/).map(x=>x.trim()).filter(Boolean);
}
function uniqueText(items){
  const seen=new Set(),out=[];
  for(const item of items){
    const clean=normalizeSpace(String(item||"").replace(/^[-–—*•\d.)\s]+/,""));
    const key=clean.toLowerCase().replace(/[^a-z0-9]+/g," ").trim();
    if(clean&&key&&!seen.has(key)){seen.add(key);out.push(clean);}
  }
  return out;
}
function markdownTitle(md){
  const m=String(md||"").match(/^#\s+(.+)$/m);
  return m?normalizeSpace(m[1]):"";
}
function sectionText(text,headings){
  const src=String(text||"");
  if(!src)return "";
  const names=headings.map(escapeRegExp).join("|");
  const re=new RegExp("(?:^|\\n|[.!?]\\s+)#{0,4}\\s*(?:"+names+")\\s*:?\\s*","i");
  const m=re.exec(src);
  if(!m)return "";
  const rest=src.slice(m.index+m[0].length);
  const stop=rest.search(/\n#{1,4}\s+[^\n]+|(?:\n|[.!?]\s+)(?:Qualifications?|Requirements?|Skills?|Education|Experience|Benefits?|About(?: us)?|How to apply|Job details?|Responsibilities?|What you(?:'ll| will) do)\s*:?/i);
  return (stop>=0?rest.slice(0,stop):rest).trim();
}
function shortenBullet(s){
  let x=normalizeSpace(s);
  if(x.length>180){
    const first=x.split(/(?<=[.!?])\s/)[0];
    x=first.length>=35?first:x.slice(0,180).replace(/\s+\S*$/,"");
  }
  return x.replace(/[.;,:]+$/,"").trim();
}
function splitResponsibilities(s){
  const text=String(s||"");
  if(!text)return [];
  const focused=sectionText(text,["Key job responsibilities","Job responsibilities","Responsibilities","What you will do","What you'll do","Your role","Duties","Key responsibilities"]);
  const source=focused||text;
  const splitter=new RegExp("\\n\\s*(?:[-*•]|\\d+[.)])\\s+|\\n+|;(?=\\s+[A-Z])|(?<=[.!?])\\s+(?=(?:"+ACTION_VERBS+")\\b)","i");
  let items=source.split(splitter).map(shortenBullet).filter(x=>x.length>=20&&x.length<=220);
  const action=new RegExp("^(?:"+ACTION_VERBS+")\\b","i");
  const actionItems=items.filter(x=>action.test(x));
  if(actionItems.length>=3)items=actionItems;
  return uniqueText(items).slice(0,6);
}
function cleanDescription(s,role="",company=""){
  const src=stripHtml(s);
  if(!src)return "";
  const before=src.split(/(?:\n|\.\s+)(?:key job responsibilities|job responsibilities|responsibilities|what you will do|what you'll do|qualifications?|requirements?)\s*:?/i)[0].trim();
  const source=before.length>=100?before:src;
  const bad=/(privacy|cookie|equal opportunity|accommodation|recruiting tips|terms of use|copyright|join our talent|sign up|apply now|share this job)/i;
  const roleWords=String(role||"").toLowerCase().split(/\W+/).filter(x=>x.length>3);
  const scored=sentenceList(source).filter(x=>x.length>=35&&x.length<=360&&!bad.test(x)).map((x,i)=>{
    const lower=x.toLowerCase();let score=Math.max(0,5-i);
    if(/responsib|role|team|work|develop|design|build|test|engineer|analyt|support|deliver|client/.test(lower))score+=4;
    for(const w of roleWords)if(lower.includes(w))score+=2;
    return {x,score};
  }).sort((a,b)=>b.score-a.score);
  const picked=[];let total=0;
  for(const row of scored){
    if(picked.length>=3)break;
    if(picked.includes(row.x))continue;
    if(total+row.x.length>520&&picked.length>=2)continue;
    picked.push(row.x);total+=row.x.length;
  }
  let summary=normalizeSpace(picked.length?picked.join(" "):source.slice(0,520));
  if(summary.length>560)summary=summary.slice(0,560).replace(/\s+\S*$/,"").trim();
  if(summary&&!/[.!?]$/.test(summary))summary+=".";
  if(summary.length<45&&role)return (company||"The company")+" is hiring for "+role+". Review the official posting for complete role details.";
  return summary;
}
function cleanEligibility(raw,descriptionSource){
  const explicit=stripHtml(raw);
  const source=explicit||stripHtml(descriptionSource);
  if(!source)return "";
  const focused=sectionText(source,["Qualifications","Requirements","Required qualifications","Minimum qualifications","What you need","Eligibility","Education","Skills"])||source;
  const signals=/(bachelor|master|degree|b\.e\.?|b\.tech|m\.tech|mba|graduate|qualification|minimum|years? of experience|experience required|required|must have|preferred|proficien|knowledge|familiarity|sql|python|java|testing|analytics|engineering|computer science)/i;
  let lines=focused.split(/\n\s*(?:[-*•]|\d+[.)])\s+|\n+|(?<=[.!?])\s+(?=[A-Z0-9])/).map(shortenBullet).filter(x=>x.length>=20&&x.length<=240&&signals.test(x));
  lines=uniqueText(lines).slice(0,5);
  if(lines.length)return lines.join(" • ");
  if(explicit)return normalizeSpace(explicit).slice(0,600);
  return "";
}
function labeledValue(text,labels){
  const list=Array.isArray(labels)?labels:[labels];
  for(const label of list){
    const re=new RegExp("(?:^|\\n|[|•])\\s*"+escapeRegExp(label)+"\\s*[:\\-]\\s*([^\\n|•]{2,220})","i");
    const m=String(text||"").match(re);
    if(m)return normalizeSpace(m[1]);
  }
  return "";
}


function queryHint(u,names){
  for(const n of names){
    const v=u.searchParams.get(n);
    if(v)return normalizeSpace(v.replace(/[+_]+/g," "));
  }
  return "";
}
function inferCompanyFromHost(host){
  const h=String(host||"").toLowerCase().replace(/^www\./,"");
  for(const [needle,name] of COMPANY_HOST_HINTS)if(h.includes(needle))return name;
  for(const ats of ATS_HOSTS){
    if(h.endsWith(ats)){
      const first=h.split(".")[0].replace(/[-_]+/g," ");
      if(first&&!/^(www|jobs|careers|wd\d+|hcm|myworkdayjobs)$/i.test(first))return titleCase(first);
    }
  }
  const labels=h.split(".").filter(Boolean);
  if(labels.length>=2){
    let x=labels[labels.length-2];
    if(["co","com","org","net"].includes(x)&&labels.length>=3)x=labels[labels.length-3];
    if(x&&!/^(jobs|careers|career|recruiting|recruitment)$/i.test(x))return titleCase(x.replace(/[-_]+/g," "));
  }
  return "";
}
function inferLocationFromUrl(u){
  const q=queryHint(u,["location","joblocation","city","jobLocation","locationName"]);
  if(q)return q;
  const raw=decodeURIComponent(u.pathname.replace(/[\/_-]+/g," ")).toLowerCase();
  const hit=INDIA_CITIES.find(c=>raw.includes(c));
  if(!hit)return "";
  return titleCase(hit==="bangalore"?"Bengaluru":hit);
}
function inferRoleFromUrl(u){
  const q=queryHint(u,["jobtitle","jobTitle","title","position","positionTitle","job_name","jobName"]);
  if(q)return q.replace(/\|.*$/,"").trim();
  const parts=u.pathname.split("/").map(x=>decodeURIComponent(x)).filter(Boolean);
  const stop=/^(en|en-us|en_us|jobs?|careers?|career|jobdetail|job-details?|positions?|opportunities|search|apply|candidateexperience|sites?)$/i;
  const candidates=parts.filter(p=>!stop.test(p)&&!/^\d{4,}$/.test(p)&&!/^[A-Z]*\d{4,}[A-Z0-9_-]*$/i.test(p));
  let x=candidates[candidates.length-1]||"";
  x=x.replace(/[_-]+/g," ").replace(/\b(?:job|opening|position)\b$/i,"").trim();
  for(const city of INDIA_CITIES)x=x.replace(new RegExp("(?:[-,| ]+)?"+escapeRegExp(city).replace(/\\ /g,"[ -]")+"$","i"),"").trim();
  return x?titleCase(x):"";
}
function extractJobId(u){
  const q=queryHint(u,["jobId","jobid","job_id","reqId","reqid","requisitionId","requisitionid","postingId","id"]);
  if(q&&/^[-A-Z0-9_]+$/i.test(q))return q;
  const parts=u.pathname.split("/").filter(Boolean).reverse();
  for(const p of parts){
    const m=decodeURIComponent(p).match(/(?:^|[_-])([A-Z]*\d{4,}[A-Z0-9_-]*)$/i);
    if(m)return m[1];
    if(/^\d{5,}$/.test(p))return p;
  }
  return "";
}
function cleanTitle(raw,company){
  let x=normalizeSpace(stripHtml(raw));
  if(!x)return "";
  x=x.replace(/\s+[|–—]\s+(?:careers?|jobs?|job search).*$/i,"").replace(/\s+-\s+(?:careers?|jobs?|job search).*$/i,"");
  if(company)x=x.replace(new RegExp("\\s+[|–—-]\\s+"+escapeRegExp(company)+".*$","i"),"");
  return x.trim();
}
function detectExperienceText(text){
  const raw=stripHtml(text);
  let m=raw.match(/(?:minimum(?: of)?|at least|more than|over)?\s*(\d+)\s*(?:\+|plus)?\s*(?:-|–|to)\s*(\d+)\s*years?(?:\s+of)?\s+experience/i);
  if(!m)m=raw.match(/(\d+)\s*(?:-|–|to)\s*(\d+)\s*years?/i);
  if(m)return {known:true,type:Number(m[1])>0?"experienced":"fresher",years:m[1]+"-"+m[2]+" years"};
  m=raw.match(/(?:minimum(?: of)?|at least|more than|over)?\s*(\d+)\s*(?:\+|plus)?\s*years?(?:\s+of)?\s+experience/i);
  if(m)return {known:true,type:Number(m[1])>0?"experienced":"fresher",years:m[1]+"+ years"};
  if(/\b(fresher|freshers|entry[- ]level|no experience required|0\s*(?:-|to)\s*1\s*year)/i.test(raw))return {known:true,type:"fresher",years:"0 years"};
  return {known:false,type:"fresher",years:"Not Specified"};
}
function readerFields(reader){
  const md=reader&&reader.content||"";
  return {
    title:cleanTitle(reader&&reader.title||markdownTitle(md),""),
    company:labeledValue(md,["Company","Organization","Employer"]),
    location:labeledValue(md,["Location","Job Location","Primary Location","Locations","City"]),
    experience:labeledValue(md,["Experience","Years of Experience","Experience Required"]),
    salary:labeledValue(md,["Salary","Compensation","Salary / Stipend","Pay Range"]),
    posted:labeledValue(md,["Date Posted","Posted","Posting Date"]),
    eligibility:sectionText(md,["Qualifications","Requirements","Required qualifications","Minimum qualifications","Eligibility","What you need","Skills"]),
    responsibilities:sectionText(md,["Key job responsibilities","Job responsibilities","Responsibilities","What you will do","What you'll do","Duties","Your role"]),
    description:sectionText(md,["Job Description","Role overview","Position summary","About the role","The role","Job summary"])||md
  };
}
function scoreJobObject(obj,jobId){
  let score=0;
  for(const [k,v] of Object.entries(obj||{})){
    const nk=normKey(k),tv=textValue(v);
    if(jobId&&tv===jobId)score+=/jobid|requisitionid|reqid|jobnumber|postingid/.test(nk)?35:12;
    if(/jobtitle|positiontitle|postingtitle|jobname|title/.test(nk)&&tv)score+=7;
    if(/jobdescription|description|jobdesc/.test(nk)&&tv.length>80)score+=7;
    if(/location|city|country/.test(nk)&&tv)score+=3;
    if(/qualification|responsibil|requirement|skill/.test(nk)&&tv)score+=3;
  }
  return score;
}
function findBestJobObject(values,jobId){
  let best=null,bestScore=0;
  for(const root of values){
    for(const obj of walkObjects(root,[])){
      const score=scoreJobObject(obj,jobId);
      if(score>bestScore){bestScore=score;best=obj;}
    }
  }
  return bestScore>=10?best:null;
}
function genericEmbedded(values,jobId){
  const obj=findBestJobObject(values,jobId);
  if(!obj)return null;
  return {
    title:deepField(obj,["jobTitle","positionTitle","postingTitle","title","jobName","name"]),
    company:deepField(obj,["companyName","employerName","organizationName","hiringOrganization","brandName"]),
    description:deepField(obj,["jobDescription","description","jobDesc","descriptionHtml","details"]),
    location:deepField(obj,["primaryLocation","jobLocation","location","locations","city","locationName"]),
    eligibility:deepField(obj,["qualifications","requiredQualifications","minimumQualifications","educationRequirements","requirements","skills"]),
    responsibilities:deepField(obj,["responsibilities","jobResponsibilities","duties","keyResponsibilities"]),
    posted:deepField(obj,["datePosted","postedDate","postingDate","createdDate","publishDate"]),
    salary:deepField(obj,["salary","salaryText","compensation","baseSalary"])
  };
}
function qualityScore(x){
  let n=0;
  if(x.title)n+=18;if(x.company)n+=14;if(x.location&&x.location!=="Not Specified")n+=12;
  if(x.description&&x.description.length>100)n+=18;if(x.responsibilities&&x.responsibilities.length>=3)n+=16;
  if(x.eligibility&&x.eligibility.length>30)n+=12;if(x.experience)n+=6;if(x.structured)n+=4;
  return Math.min(100,n);
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


function extractSkills(text){
  const raw=stripHtml(text||"");
  const defs=[
    ["Java",/\bjava\b/i],["Python",/\bpython\b/i],["SQL",/\bsql\b/i],["JavaScript",/\bjavascript\b|\bjs\b/i],
    ["React",/\breact(?:\.js)?\b/i],["Angular",/\bangular\b/i],["Spring Boot",/\bspring\s*boot\b/i],
    ["AWS",/\baws\b|amazon web services/i],["Azure",/\bazure\b/i],["Google Cloud",/\bgcp\b|google cloud/i],
    ["ETL",/\betl\b|extract[, ]+transform[, ]+load/i],["Snowflake",/\bsnowflake\b/i],["Databricks",/\bdatabricks\b/i],
    ["Linux",/\blinux\b/i],["Docker",/\bdocker\b/i],["Kubernetes",/\bkubernetes\b|\bk8s\b/i],
    ["Excel",/\bexcel\b/i],["Power BI",/\bpower\s*bi\b/i],["Tableau",/\btableau\b/i],
    ["Data Analysis",/\bdata analy(?:sis|tics)\b/i],["Data Engineering",/\bdata engineering\b/i],
    ["Communication",/\bcommunication\b/i],["Problem Solving",/\bproblem[- ]solving\b/i]
  ];
  const out=[];
  for(const [label,re] of defs){if(re.test(raw)&&!out.includes(label))out.push(label);if(out.length>=7)break;}
  return out.length?out:["Role-specific skills from the official posting"];
}
function inferWorkMode(text,location){
  const raw=(stripHtml(text||"")+" "+String(location||"")).toLowerCase();
  if(/\bhybrid\b/.test(raw))return "Hybrid";
  if(/\bremote\b|work from home|\bwfh\b/.test(raw))return "Remote";
  if(/\bon[- ]site\b|\bonsite\b|work from office|\bwfo\b/.test(raw))return "On-site";
  return "Not Specified";
}
function whoShouldApply(exp,eligibility){
  const years=String(exp&&exp.years||"Not Specified");
  if(exp&&exp.type==="fresher"){
    return "Freshers and early-career candidates who match the education and skill requirements in the official posting should review this opportunity. Experience listed: "+years+".";
  }
  return "Experienced candidates whose background matches the official education, skill and experience requirements should review this opportunity. Experience listed: "+years+".";
}

export default async function handler(req,res){
  if(req.method!=="POST"){
    res.setHeader("Allow","POST");
    return res.status(405).json({error:"Method not allowed"});
  }

  res.setHeader("Cache-Control","no-store");
  if(!requireAdmin(req,res))return;

  try{
    const input=String(req.body&&req.body.url||"").trim();
    if(!input)return res.status(400).json({error:"Job URL is required."});

    const original=await assertPublicUrl(input);
    const hint=normalizeKnownCareerUrl(original.href);
    const sourceUrl=hint.applyUrl||original.href;
    const sourceHost=new URL(sourceUrl).hostname.replace(/^www\./,"");
    const urlCompany=hint.companyHint||inferCompanyFromHost(sourceHost);
    const urlRole=hint.roleHint||inferRoleFromUrl(original);
    const urlLocation=hint.locationHint||inferLocationFromUrl(original);
    const jobId=extractJobId(original);

    let page={html:"",url:hint.fetchUrl||sourceUrl};
    let directError="";
    try{
      page=await fetchHtml(hint.fetchUrl||sourceUrl);
    }catch(error){
      directError=error&&error.message||"Direct fetch failed";
    }

    const html=page.html||"";
    const pageText=stripHtml(html);
    const jsonRoots=[...collectJsonLd(html),...collectEmbeddedJson(html)];
    const nextData=collectNextData(html);
    if(nextData)jsonRoots.push(nextData);

    let structured=null;
    for(const root of jsonRoots){structured=findJobPosting(root);if(structured)break;}
    const ibm=ibmFallback(nextData,input);
    const embedded=genericEmbedded(jsonRoots,jobId);

    let company=getCompany(structured)||(ibm&&ibm.company)||(embedded&&embedded.company)||hint.companyHint||meta(html,null,"og:site_name")||urlCompany;
    company=normalizeSpace(company).replace(/\s+(?:careers?|jobs?)$/i,"").trim();

    let title=cleanTitle(textValue(structured&&structured.title)||(ibm&&ibm.title)||(embedded&&embedded.title)||headingOne(html)||meta(html,null,"og:title")||titleTag(html)||urlRole,company);
    let location=getLocation(structured)||(ibm&&ibm.location)||(embedded&&embedded.location)||labeledValue(pageText,["Job Location","Primary Location","Location","City"])||urlLocation;

    let rawDescription=textValue(structured&&structured.description)||(ibm&&ibm.description)||(embedded&&embedded.description)||meta(html,"description")||meta(html,null,"og:description")||"";
    let rawEligibility=textValue(structured&&structured.qualifications)||textValue(structured&&structured.educationRequirements)||textValue(structured&&structured.experienceRequirements)||(ibm&&ibm.eligibility)||(embedded&&embedded.eligibility)||"";
    let rawResponsibilities=textValue(structured&&structured.responsibilities)||(ibm&&ibm.responsibilities&&ibm.responsibilities.join("\n"))||(embedded&&embedded.responsibilities)||rawDescription;
    let salary=getSalary(structured)||(embedded&&embedded.salary)||"";
    let posted=textValue(structured&&structured.datePosted)||(ibm&&ibm.posted)||(embedded&&embedded.posted)||"";

    let description=cleanDescription(rawDescription,title,company);
    let responsibilities=splitResponsibilities(rawResponsibilities);
    let eligibility=cleanEligibility(rawEligibility,rawDescription);
    let exp=detectExperienceText([textValue(structured&&structured.experienceRequirements),rawEligibility,rawDescription,pageText.slice(0,25000)].filter(Boolean).join(" "));

    const sparse=!(title&&company&&location&&description&&responsibilities.length>=3&&eligibility);
    let reader=null;
    let readerError="";
    if(sparse){
      try{
        reader=await fetchReader(hint.fetchUrl||sourceUrl);
      }catch(error){
        readerError=error&&error.message||"Reader fallback failed";
      }

      if(reader){
        const rf=readerFields(reader);
        company=company||rf.company||urlCompany;
        title=title||cleanTitle(rf.title,company)||urlRole;
        location=(location&&location!=="Not Specified"?location:"")||rf.location||urlLocation;
        if(!rawDescription||description.length<100)rawDescription=rf.description||rawDescription;
        if(!rawEligibility)rawEligibility=rf.eligibility||rawEligibility;
        if(!rawResponsibilities||responsibilities.length<3)rawResponsibilities=rf.responsibilities||rf.description||rawResponsibilities;
        salary=salary||rf.salary;
        posted=posted||rf.posted;
        description=cleanDescription(rawDescription,title,company);
        eligibility=cleanEligibility(rawEligibility,rawDescription);
        responsibilities=splitResponsibilities(rawResponsibilities);
        exp=detectExperienceText([rf.experience,rawEligibility,rawDescription].filter(Boolean).join(" "));
      }
    }

    company=company||urlCompany||"Company Not Identified";
    title=title||urlRole||"Job Opening";
    location=normalizeSpace(location)||"Not Specified";
    const domain=hint.domainHint||sourceHost;
    const logoUrl=organizationLogo(jsonRoots,structured,company,html,page.url||sourceUrl);

    description=description||((company!=="Company Not Identified"?company:"The company")+" is hiring for "+title+(location!=="Not Specified"?" in "+location:"")+". Review the official job posting for complete role details.");
    eligibility=eligibility||"Review the official job posting for education, skills and experience requirements.";
    if(!responsibilities.length)responsibilities=["Review the official job description for role-specific responsibilities before applying."];
    salary=normalizeSpace(salary)||"Not Disclosed";

    const category=inferCategory(title,description,domain,exp);
    const structuredOk=Boolean(structured);
    const confidence=qualityScore({title:title!=="Job Opening",company:company!=="Company Not Identified",location,description,responsibilities,eligibility,experience:exp.known,structured:structuredOk});

    const data={
      sourceUrl,
      domain,
      company,
      salary,
      logo:[initials(company),"#0b6fe8"],
      logoUrl,
      role:title,
      roleTag:title,
      loc:location,
      locationFilter:location==="Not Specified"?"":location,
      batch:"Not Specified",
      elig:eligibility,
      cat:category,
      expType:exp.type,
      expYears:exp.years,
      date:formatDate(posted),
      desc:description,
      resp:responsibilities.slice(0,6),
      apply:sourceUrl,
      page:"jobs/"+slugify(company+"-"+title)+".html",
      status:"active",
      verifiedDate:formatDate(new Date().toISOString()),
      sourceName:"Official "+company+" careers page",
      skills:extractSkills([rawEligibility,rawDescription].filter(Boolean).join(" ")),
      who:whoShouldApply(exp,eligibility),
      workMode:inferWorkMode([rawDescription,pageText.slice(0,12000)].filter(Boolean).join(" "),location),
      contentPlan:{
        version:"expanded-job-page-v1",
        generatedSections:["Job overview","Eligibility","Skills","Responsibilities","Who should apply","HD Careers guidance","Resume guidance","Preparation guide","Application checklist"],
        targetWords:1000
      },
      extraction:{
        source:structuredOk?"structured":reader?"reader":embedded?"embedded":"url-fallback",
        confidence,
        structuredJobPosting:structuredOk,
        title:Boolean(title&&title!=="Job Opening"),
        company:Boolean(company&&company!=="Company Not Identified"),
        location:location!=="Not Specified",
        salary:salary!=="Not Disclosed",
        eligibility:!eligibility.startsWith("Review the official job posting"),
        description:description.length>=80&&!description.includes("Review the official job posting for complete role details"),
        responsibilities:responsibilities.length>=3&&!responsibilities[0].startsWith("Review the official job description"),
        experience:exp.known,
        directFetch:Boolean(html),
        readerFallback:Boolean(reader),
        directError,
        readerError
      }
    };

    return res.status(200).json({ok:true,data});
  }catch(error){
    const msg=error&&error.name==="AbortError"?"The job page took too long to respond.":(error&&error.message)||"Could not extract the job page.";
    return res.status(400).json({error:msg});
  }
}
