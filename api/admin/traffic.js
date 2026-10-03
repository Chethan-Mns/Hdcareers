import crypto from "node:crypto";
import {requireAdmin} from "../../lib/admin-auth.js";

const ALLOWED_DAYS=new Set([1,7,30]);
const TOKEN_URL="https://oauth2.googleapis.com/token";
const SCOPE="https://www.googleapis.com/auth/analytics.readonly";

function config(){
  return {
    propertyId:String(process.env.GA4_PROPERTY_ID||"").trim(),
    clientEmail:String(process.env.GA4_CLIENT_EMAIL||"").trim(),
    privateKey:String(process.env.GA4_PRIVATE_KEY||"").replace(/\\n/g,"\n").trim()
  };
}

function b64url(input){
  return Buffer.from(input).toString("base64url");
}

async function accessToken(cfg){
  const now=Math.floor(Date.now()/1000);
  const header=b64url(JSON.stringify({alg:"RS256",typ:"JWT"}));
  const payload=b64url(JSON.stringify({
    iss:cfg.clientEmail,
    scope:SCOPE,
    aud:TOKEN_URL,
    iat:now,
    exp:now+3600
  }));
  const unsigned=header+"."+payload;
  const signer=crypto.createSign("RSA-SHA256");
  signer.update(unsigned);
  signer.end();
  const assertion=unsigned+"."+signer.sign(cfg.privateKey,"base64url");
  const body=new URLSearchParams({
    grant_type:"urn:ietf:params:oauth:grant-type:jwt-bearer",
    assertion
  });
  const r=await fetch(TOKEN_URL,{
    method:"POST",
    headers:{"content-type":"application/x-www-form-urlencoded"},
    body
  });
  const data=await r.json().catch(()=>({}));
  if(!r.ok||!data.access_token)throw new Error(data.error_description||data.error||"Could not authorize Google Analytics.");
  return data.access_token;
}

async function ga(token,propertyId,method,body){
  const r=await fetch("https://analyticsdata.googleapis.com/v1beta/properties/"+encodeURIComponent(propertyId)+":"+method,{
    method:"POST",
    headers:{Authorization:"Bearer "+token,"content-type":"application/json"},
    body:JSON.stringify(body)
  });
  const data=await r.json().catch(()=>({}));
  if(!r.ok)throw new Error(data.error?.message||("Google Analytics request failed ("+r.status+")"));
  return data;
}

function metric(row,index=0){
  return Number(row?.metricValues?.[index]?.value||0);
}

function dim(row,index=0){
  return String(row?.dimensionValues?.[index]?.value||"");
}

function rows(report,key,metricName){
  return (report?.rows||[]).map(r=>({[key]:dim(r),[metricName]:metric(r)}));
}

function canonicalPath(value){
  const path=String(value||"/").split("?")[0]||"/";
  return path==="/index.html"?"/":path;
}

function mergedPageRows(report,limit=10){
  const merged=new Map();
  for(const r of report?.rows||[]){
    const path=canonicalPath(dim(r));
    merged.set(path,(merged.get(path)||0)+metric(r));
  }
  return [...merged.entries()]
    .map(([requestPath,pageviews])=>({requestPath,pageviews}))
    .sort((a,b)=>b.pageviews-a.pageviews)
    .slice(0,limit);
}

function exactFilter(fieldName,value){
  return {filter:{fieldName,stringFilter:{matchType:"EXACT",value,caseSensitive:false}}};
}

function inListFilter(fieldName,values){
  return {filter:{fieldName,inListFilter:{values,caseSensitive:false}}};
}

function sleep(ms){
  return new Promise(resolve=>setTimeout(resolve,ms));
}

async function loadReports(cfg,startDate){
  let lastError;
  for(let attempt=1;attempt<=2;attempt++){
    try{
      const token=await accessToken(cfg);
      const eventNames=["job_open","job_apply_click","resume_checker_use","resume_checker_sample","share_click","social_click"];
      const reports=await Promise.all([
        ga(token,cfg.propertyId,"runRealtimeReport",{metrics:[{name:"activeUsers"}]}),
        ga(token,cfg.propertyId,"runReport",{dateRanges:[{startDate,endDate:"today"}],metrics:[{name:"activeUsers"},{name:"screenPageViews"},{name:"sessions"}]}),
        ga(token,cfg.propertyId,"runReport",{dateRanges:[{startDate,endDate:"today"}],dimensions:[{name:"pagePath"}],metrics:[{name:"screenPageViews"}],orderBys:[{metric:{metricName:"screenPageViews"},desc:true}],limit:"20"}),
        ga(token,cfg.propertyId,"runReport",{dateRanges:[{startDate,endDate:"today"}],dimensions:[{name:"sessionSourceMedium"}],metrics:[{name:"sessions"}],orderBys:[{metric:{metricName:"sessions"},desc:true}],limit:"10"}),
        ga(token,cfg.propertyId,"runReport",{dateRanges:[{startDate,endDate:"today"}],dimensions:[{name:"country"}],metrics:[{name:"activeUsers"}],orderBys:[{metric:{metricName:"activeUsers"},desc:true}],limit:"10"}),
        ga(token,cfg.propertyId,"runReport",{dateRanges:[{startDate,endDate:"today"}],dimensions:[{name:"deviceCategory"}],metrics:[{name:"activeUsers"}],orderBys:[{metric:{metricName:"activeUsers"},desc:true}],limit:"10"}),
        ga(token,cfg.propertyId,"runReport",{dateRanges:[{startDate,endDate:"today"}],dimensions:[{name:"eventName"}],metrics:[{name:"eventCount"},{name:"activeUsers"}],dimensionFilter:inListFilter("eventName",eventNames),limit:"50"}),
        ga(token,cfg.propertyId,"runReport",{dateRanges:[{startDate,endDate:"today"}],metrics:[{name:"screenPageViews"}],dimensionFilter:{filter:{fieldName:"pagePath",stringFilter:{matchType:"BEGINS_WITH",value:"/jobs/",caseSensitive:false}}}}),
        ga(token,cfg.propertyId,"runReport",{dateRanges:[{startDate,endDate:"today"}],dimensions:[{name:"pagePath"}],metrics:[{name:"eventCount"}],dimensionFilter:exactFilter("eventName","job_apply_click"),orderBys:[{metric:{metricName:"eventCount"},desc:true}],limit:"10"}),
        ga(token,cfg.propertyId,"runReport",{dateRanges:[{startDate,endDate:"today"}],dimensions:[{name:"pagePath"}],metrics:[{name:"eventCount"}],dimensionFilter:exactFilter("eventName","resume_checker_use"),orderBys:[{metric:{metricName:"eventCount"},desc:true}],limit:"10"}),
        ga(token,cfg.propertyId,"runReport",{dateRanges:[{startDate,endDate:"today"}],dimensions:[{name:"sessionSourceMedium"}],metrics:[{name:"eventCount"}],dimensionFilter:exactFilter("eventName","job_apply_click"),orderBys:[{metric:{metricName:"eventCount"},desc:true}],limit:"10"})
      ]);
      return reports;
    }catch(error){
      lastError=error;
      if(attempt<2)await sleep(650);
    }
  }
  throw lastError;
}

export default async function handler(req,res){
  res.setHeader("Cache-Control","private, max-age=0, no-store");
  if(!requireAdmin(req,res))return;
  if(req.method!=="GET"){
    res.setHeader("Allow","GET");
    return res.status(405).json({error:"Method not allowed."});
  }

  const days=Number(req.query?.days||7);
  if(!ALLOWED_DAYS.has(days))return res.status(400).json({error:"days must be 1, 7 or 30."});

  const cfg=config();
  const missing=[];
  if(!cfg.propertyId)missing.push("GA4_PROPERTY_ID");
  if(!cfg.clientEmail)missing.push("GA4_CLIENT_EMAIL");
  if(!cfg.privateKey)missing.push("GA4_PRIVATE_KEY");
  if(missing.length)return res.status(503).json({configured:false,missing,error:"Google Analytics API credentials are incomplete."});

  const startDate=days===1?"today":(days-1)+"daysAgo";
  try{
    const [
      realtime,
      totals,
      pages,
      sources,
      countries,
      devices,
      eventSummary,
      jobViews,
      applyJobs,
      resumeJobs,
      applySources
    ]=await loadReports(cfg,startDate);

    const totalRow=totals?.rows?.[0];
    const eventMap=new Map((eventSummary?.rows||[]).map(r=>[dim(r),{count:metric(r,0),users:metric(r,1)}]));
    const eventValue=name=>eventMap.get(name)||{count:0,users:0};
    const apply=eventValue("job_apply_click");
    const resume=eventValue("resume_checker_use");
    const jobPageViews=metric(jobViews?.rows?.[0]);
    return res.status(200).json({
      configured:true,
      provider:"ga4",
      days,
      realtimeUsers:metric(realtime?.rows?.[0]),
      totals:{
        visitors:metric(totalRow,0),
        pageviews:metric(totalRow,1),
        sessions:metric(totalRow,2)
      },
      pages:mergedPageRows(pages),
      referrers:rows(sources,"referrerHostname","sessions"),
      countries:rows(countries,"country","visitors"),
      devices:rows(devices,"deviceType","visitors"),
      conversions:{
        jobPageViews,
        jobOpens:eventValue("job_open").count,
        applyClicks:apply.count,
        applyUsers:apply.users,
        resumeChecks:resume.count,
        resumeUsers:resume.users,
        resumeSamples:eventValue("resume_checker_sample").count,
        shares:eventValue("share_click").count,
        socialClicks:eventValue("social_click").count,
        applyRate:jobPageViews?Number((apply.count/jobPageViews*100).toFixed(1)):0
      },
      applyJobs:rows(applyJobs,"requestPath","count").map(x=>({...x,requestPath:canonicalPath(x.requestPath)})),
      resumeJobs:rows(resumeJobs,"requestPath","count").map(x=>({...x,requestPath:canonicalPath(x.requestPath)})),
      applySources:rows(applySources,"referrerHostname","count"),
      refreshedAt:new Date().toISOString()
    });
  }catch(err){
    return res.status(502).json({configured:true,provider:"ga4",error:err.message||"Could not load Google Analytics data."});
  }
}
