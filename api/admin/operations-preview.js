import {requireAdmin} from "../../lib/admin-auth.js";

// Read-only v2 preview telemetry. Never writes to production.
const REPO=process.env.ADMIN_GITHUB_REPO||"Chethan-Mns/Hdcareers";
const REF=process.env.ADMIN_GITHUB_BASE||"main";
const PATHS=[
  "data/jobs.json",
  "data/telegram-deliveries.json",
  "data/telegram-hourly-queue.json",
  "data/availability-status.json",
  "data/daily-review-batch.json"
];
export const config={maxDuration:30};
function clean(v){return String(v||"").slice(0,400)}
async function api(path,token){
  const controller=new AbortController();
  const timer=setTimeout(()=>controller.abort(),10000);
  try{
    const r=await fetch("https://api.github.com/repos/"+REPO+path,{
      headers:{accept:"application/vnd.github+json",authorization:"Bearer "+token,
        "x-github-api-version":"2022-11-28","user-agent":"HD-Careers-Admin-V2-Read-Only-Preview"},
      cache:"no-store",signal:controller.signal});
    if(!r.ok)throw new Error("GitHub status "+r.status);
    return await r.json();
  }finally{clearTimeout(timer)}
}
function readFile(path,token){return api("/contents/"+path+"?ref="+encodeURIComponent(REF),token).then(x=>
  JSON.parse(Buffer.from(String(x.content||"").replace(/\n/g,""),"base64").toString("utf8")))}
function isRec(x){return x&&typeof x==="object"}
async function publicSiteCheck(job){
  const page=String(job?.page||"");
  if(!/^jobs\/[a-z0-9-]+\.html$/.test(page))return "unknown";
  const controller=new AbortController();
  const timer=setTimeout(()=>controller.abort(),4000);
  try{
    const r=await fetch("https://hdcareers.in/"+page,{cache:"no-store",signal:controller.signal});
    if(!r.ok)return "not_confirmed";
    const html=(await r.text()).replaceAll("&amp;","&");
    return html.includes(String(job.apply||""))?"live":"not_confirmed";
  }catch{return "unknown"}finally{clearTimeout(timer)}
}
export default async function handler(req,res){
  res.setHeader("Cache-Control","private,no-store");
  res.setHeader("X-Robots-Tag","noindex,nofollow");
  if(req.method!=="GET"){res.setHeader("Allow","GET");return res.status(405).json({error:"Read-only preview."})}
  if(process.env.VERCEL_ENV==="production")return res.status(404).json({error:"Preview telemetry is not available in production."});
  if(!await requireAdmin(req,res,["owner","job_editor"]))return;
  const token=process.env.GITHUB_PUBLISH_TOKEN;
  if(!token)return res.status(503).json({error:"Preview GitHub read credentials are not configured. Use interactive demo mode."});
  try{
    const paths=PATHS.map(p=>readFile(p,token));
    const work=api("/actions/workflows/admin-job-generator.yml/runs?per_page=6",token);
    const hourly=api("/actions/workflows/hourly-telegram-queue.yml/runs?per_page=6",token).catch(()=>({workflow_runs:[]}));
    const runs=await Promise.allSettled([...paths,work,hourly]);
    const get=(i,fallback)=>runs[i].status==="fulfilled"?runs[i].value:fallback;
    const jobs=Array.isArray(get(0,[]))?get(0,[]):[];
    const receipts=isRec(get(1,{}))?get(1,{}):{};
    const queue=get(2,{items:[]});
    const expiry=get(3,{});
    const batch=get(4,{});
    const publishing=get(5,{workflow_runs:[]});
    const hourlyRuns=get(6,{workflow_runs:[]});
    const lastJobs=[...jobs].sort((a,b)=>Number(b.id||0)-Number(a.id||0)).slice(0,12);
    const delivered=Object.values(receipts).filter(x=>x&&x.status==="delivered");
    const queueItems=Array.isArray(queue?.items)?queue.items:[];
    const publicStates=await Promise.all(lastJobs.map(j=>publicSiteCheck(j)));
    const list=lastJobs.map((j,i)=>{
      const evidence=Object.values(receipts).find(x=>x&&x.page===j.page&&x.status==="delivered");
      const uncertain=Object.values(receipts).find(x=>x&&x.page===j.page&&x.status==="uncertain");
      const queued=queueItems.find(x=>x.page===j.page);
      return {id:j.id,company:clean(j.company),role:clean(j.role),location:clean(j.loc),
        page:j.page,apply:j.apply,status:j.status,site:publicStates[i],
        telegram:evidence?"delivered":uncertain?"uncertain":queued?.status||"not_queued",
        messageId:evidence?.messageId||null,deliveryAt:evidence?.deliveredAt||null,
        queueAt:queued?.queuedAt||null};
    });
    const runsSlim=(data)=>(Array.isArray(data?.workflow_runs)?data.workflow_runs:[]).slice(0,6).map(x=>({
      id:x.id,status:x.status,conclusion:x.conclusion,event:x.event,createdAt:x.created_at,
      updatedAt:x.updated_at,url:x.html_url,commit:x.head_sha?.slice(0,12)
    }));
    const latestRun=runsSlim(publishing)[0];
    let commitSteps=[];
    if(latestRun?.id){
      try{
        const d=await api("/actions/runs/"+latestRun.id+"/jobs?per_page=5",token);
        commitSteps=(d.jobs||[]).flatMap(j=>(j.steps||[]).map(s=>({
          name:clean(s.name),status:s.status,conclusion:s.conclusion
        }))).slice(0,30);
      }catch{}
    }
    res.status(200).json({
      mode:"live-read-only",source:"production main branch and hdcareers.in",
      checkedAt:new Date().toISOString(),
      jobs:list,
      counts:{published:jobs.length,active:jobs.filter(x=>x.status==="active").length,
        expired:jobs.filter(x=>x.status==="expired").length,
        review:expiry.review||0,checked:expiry.checked||0,
        confirmedDeliveries:delivered.length,pendingHourly:queueItems.filter(x=>x.status==="pending").length},
      daily:{batchId:batch.batchId||"",priority:batch.priority?.length||0,backup:batch.backup?.length||0,
        status:batch.status||"waiting"},
      queue:queueItems.map(x=>({page:x.page,status:x.status,queuedAt:x.queuedAt,
        deliveredAt:x.deliveredAt||null,messageId:x.messageId||null})),
      expiryExceptions:(expiry.items||[]).filter(x=>x.state==="review").slice(0,25).map(x=>({
        id:x.id,company:clean(x.company),role:clean(x.role),reason:clean(x.reason),
        checkedAt:x.checkedAt,apply:clean(x.url),state:"review"
      })),
      runs:{publish:runsSlim(publishing),hourly:runsSlim(hourlyRuns),publishSteps:commitSteps},
      errors:runs.map((x,i)=>x.status==="rejected"?PATHS[i]||"workflow":null).filter(Boolean),
      notice:"Read-only telemetry; a READY GitHub workflow is not proof of a live application. Confirmed Telegram means recorded delivery receipt."
    });
  }catch(e){return res.status(502).json({error:"Unable to load read-only preview telemetry: "+clean(e.message)})}
}
