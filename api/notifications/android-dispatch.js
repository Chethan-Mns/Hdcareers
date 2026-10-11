import crypto from "node:crypto";
import {androidConfigured,readReviewBatch,acquire,release,devices,sent,markSent,fcmAccessToken,sendFcm,unregisterDevice} from "../../lib/android-notify.js";
function authorized(req){
  const expected=String(process.env.ANDROID_PUSH_DISPATCH_SECRET||"");
  const supplied=String(req.headers.authorization||"").replace(/^Bearer\s+/i,"");
  return expected.length>=32&&Buffer.byteLength(expected)===Buffer.byteLength(supplied)&&
    crypto.timingSafeEqual(Buffer.from(expected),Buffer.from(supplied));
}
function eligible(batch){
  const when=Date.parse(batch.generatedAt||"");
  return /^[a-zA-Z0-9_-]{6,100}$/.test(String(batch.batchId||"")) &&
    ["draft","review","ready"].includes(batch.status)&&
    Array.isArray(batch.priority)&&batch.priority.length===10 &&
    Array.isArray(batch.backup)&&batch.backup.length===10 &&
    Number.isFinite(when)&&Date.now()-when<48*3600000 && when<Date.now()+300000 &&
    batch.priority.every(x=>x.id&&x.company&&x.role&&x.apply)&&
    batch.backup.every(x=>x.id&&x.company&&x.role&&x.apply) &&
    new Set(batch.priority.map(x=>String(x.company).toLowerCase())).size===10;
}
export default async function handler(req,res){
  res.setHeader("Cache-Control","no-store");
  if(req.method!=="POST")return res.status(405).json({error:"Method not allowed."});
  if(!authorized(req))return res.status(401).json({error:"Authentication required."});
  if(!androidConfigured())return res.status(503).json({error:"Firebase and private device storage not configured."});
  let locked="";
  try{
    const batch=await readReviewBatch();
    if(!eligible(batch))return res.status(409).json({error:"No recent complete review batch is ready."});
    if(!await acquire(batch.batchId))return res.status(409).json({error:"Review batch notification already running."});
    locked=batch.batchId;
    const registered=await devices();
    const access=registered.length?await fcmAccessToken():"";
    const results=[];
    for(const d of registered){
      if(await sent(batch.batchId,d.id)) {results.push({id:d.id,status:"already-sent"});continue}
      try{
        const response=await sendFcm(d.token,{
          title:"HD Careers · 20 jobs ready",body:"Your Priority 10 and Backup 10 are ready to review.",
          batchId:batch.batchId,kind:"review"
        },access);
        if(response.ok)await markSent(batch.batchId,d.id);
        if(response.error==="UNREGISTERED")await unregisterDevice(d.id);
        results.push({id:d.id,status:response.ok?"accepted":"failed",error:response.error});
      }catch{results.push({id:d.id,status:"failed"})}
    }
    return res.status(200).json({batchId:batch.batchId,results});
  }catch{return res.status(502).json({error:"Unable to dispatch Android notifications."})}
  finally {if(locked)await release(locked).catch(()=>{})}
}
