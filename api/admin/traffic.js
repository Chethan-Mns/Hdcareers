import {requireAdmin} from "../../lib/admin-auth.js";

const ALLOWED_DAYS=new Set([1,7,30]);

function envConfig(){
  return {
    token:String(process.env.VERCEL_ANALYTICS_TOKEN||process.env.VERCEL_API_TOKEN||""),
    projectId:String(process.env.HD_VERCEL_PROJECT_ID||process.env.VERCEL_PROJECT_ID||""),
    teamId:String(process.env.HD_VERCEL_TEAM_ID||process.env.VERCEL_TEAM_ID||process.env.VERCEL_ORG_ID||"")
  };
}

async function query(path,{token,projectId,teamId},since,until,by){
  const u=new URL("https://api.vercel.com"+path);
  u.searchParams.set("projectId",projectId);
  u.searchParams.set("since",since);
  u.searchParams.set("until",until);
  if(teamId)u.searchParams.set("teamId",teamId);
  if(by){
    u.searchParams.append("by",by);
    u.searchParams.set("limit","12");
  }
  const r=await fetch(u,{headers:{Authorization:"Bearer "+token,Accept:"application/json"}});
  const body=await r.json().catch(()=>({}));
  if(!r.ok)throw new Error(body.error?.message||body.message||("Vercel Analytics request failed ("+r.status+")"));
  return body.data;
}

export default async function handler(req,res){
  res.setHeader("Cache-Control","no-store");
  if(!requireAdmin(req,res))return;
  if(req.method!=="GET"){
    res.setHeader("Allow","GET");
    return res.status(405).json({error:"Method not allowed."});
  }
  const days=Number(req.query?.days||7);
  if(!ALLOWED_DAYS.has(days))return res.status(400).json({error:"days must be 1, 7 or 30."});
  const cfg=envConfig();
  const missing=[];
  if(!cfg.token)missing.push("VERCEL_ANALYTICS_TOKEN");
  if(!cfg.projectId)missing.push("HD_VERCEL_PROJECT_ID");
  if(missing.length)return res.status(503).json({configured:false,missing,error:"Traffic dashboard needs Vercel Analytics API credentials."});

  const until=new Date().toISOString();
  const since=new Date(Date.now()-days*86400000).toISOString();
  try{
    const [totals,pages,referrers,countries,devices]=await Promise.all([
      query("/v1/query/web-analytics/visits/count",cfg,since,until),
      query("/v1/query/web-analytics/visits/aggregate",cfg,since,until,"requestPath"),
      query("/v1/query/web-analytics/visits/aggregate",cfg,since,until,"referrerHostname"),
      query("/v1/query/web-analytics/visits/aggregate",cfg,since,until,"country"),
      query("/v1/query/web-analytics/visits/aggregate",cfg,since,until,"deviceType")
    ]);
    return res.status(200).json({configured:true,days,since,until,totals:totals||{},pages:pages||[],referrers:referrers||[],countries:countries||[],devices:devices||[]});
  }catch(err){
    return res.status(502).json({configured:true,error:err.message||"Could not load Vercel Web Analytics."});
  }
}
