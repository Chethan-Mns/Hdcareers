import crypto from "node:crypto";
import {requireAdmin,auditMutation} from "./admin-auth.js";
import {redis,getUser} from "./admin-store.js";

const scope="hdpush:v1:"+(process.env.VERCEL_ENV==="preview"?"preview":"production")+":";
const indexKey=scope+"devices";
const key=id=>scope+"device:"+id;
const hmac=(user,id)=>crypto.createHash("sha256").update(user+"|"+id).digest("hex");
const safe=(a,b)=>{
 const x=Buffer.from(String(a||"")),y=Buffer.from(String(b||""));
 return x.length===y.length&&crypto.timingSafeEqual(x,y);
};
const configured=()=>Boolean(process.env.FCM_PROJECT_ID&&process.env.FCM_SERVICE_ACCOUNT_CLIENT_EMAIL&&process.env.FCM_SERVICE_ACCOUNT_PRIVATE_KEY);
let cachedToken=null,tokenExpires=0;

async function accessToken(){
 if(cachedToken&&Date.now()<tokenExpires)return cachedToken;
 if(!configured())throw Object.assign(new Error("Firebase server credentials are not configured."),{status:503});
 const email=process.env.FCM_SERVICE_ACCOUNT_CLIENT_EMAIL;
 const secret=String(process.env.FCM_SERVICE_ACCOUNT_PRIVATE_KEY).replace(/\\n/g,"\n");
 const now=Math.floor(Date.now()/1000);
 const encode=o=>Buffer.from(JSON.stringify(o)).toString("base64url");
 const head=encode({alg:"RS256",typ:"JWT"});
 const body=encode({iss:email,scope:"https://www.googleapis.com/auth/firebase.messaging",aud:"https://oauth2.googleapis.com/token",iat:now,exp:now+3500});
 const signature=crypto.createSign("RSA-SHA256").update(head+"."+body).sign(secret,"base64url");
 const assertion=head+"."+body+"."+signature;
 const response=await fetch("https://oauth2.googleapis.com/token",{
  method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},
  body:new URLSearchParams({grant_type:"urn:ietf:params:oauth:grant-type:jwt-bearer",assertion}),
  signal:AbortSignal.timeout(10000)
 });
 const obj=await response.json().catch(()=>({}));
 if(!response.ok||!obj.access_token)throw Object.assign(new Error("Firebase service account authentication failed."),{status:502});
 cachedToken=obj.access_token;
 tokenExpires=Date.now()+Math.min(3200,Math.max(120,Number(obj.expires_in||3600)-120))*1000;
 return cachedToken;
}
async function deliver(record,title,body,batchId,kind="batch"){
 const t=await accessToken();
 const url="https://fcm.googleapis.com/v1/projects/"+encodeURIComponent(process.env.FCM_PROJECT_ID)+"/messages:send";
 const response=await fetch(url,{
  method:"POST",headers:{"Authorization":"Bearer "+t,"Content-Type":"application/json"},
  body:JSON.stringify({message:{token:record.token,notification:{title,body},data:{batchId:batchId||"manual",openReview:kind==="expiry"?"0":"1",openExpiry:kind==="expiry"?"1":"0",kind},android:{priority:"HIGH",notification:{channel_id:"hd_review_updates"}}}}),
  signal:AbortSignal.timeout(12000)
 });
 if(!response.ok){
  const err=await response.json().catch(()=>({}));
  const code=String(err.error?.status||"");
  if(code==="UNREGISTERED")return {ok:false,invalid:true};
  throw Object.assign(new Error("Firebase declined push delivery."),{status:502});
 }
 return {ok:true};
}
async function readDevice(id){const raw=await redis("GET",key(id));if(!raw)return null;try{return JSON.parse(raw)}catch{return null}}
const sameOrigin=req=>{
 const origin=String(req.headers?.origin||"");if(!origin)return true;
 const host=String(req.headers?.["x-forwarded-host"]||req.headers?.host||"").toLowerCase();
 try{return new URL(origin).host.toLowerCase()===host}catch{return false}
};
export default async function adminPushHandler(req,res){
 res.setHeader("Cache-Control","private, no-store");
 const action=String(req.body?.action||"");
 const secret=process.env.ANDROID_PUSH_DISPATCH_SECRET;
 const automated=req.method==="POST"&&["notify_batch","notify_expiry"].includes(action)&&secret&&secret.length>=32&&safe(req.headers?.["x-hd-push-key"],secret);
 if(!automated&&!await requireAdmin(req,res,["owner","job_editor"]))return;
 if(!["GET","POST"].includes(req.method)){res.setHeader("Allow","GET, POST");return res.status(405).json({error:"Method not allowed"});}
 if(req.method==="POST"&&process.env.VERCEL_ENV==="preview")return res.status(403).json({error:"Push registration and delivery are disabled in Preview."});
 if(req.method==="POST"&&!automated&&!sameOrigin(req))return res.status(403).json({error:"Invalid origin."});
 try{
  if(req.method==="GET")return res.status(200).json({firebaseConfigured:configured(),serverReady:configured()&&Boolean(secret&&secret.length>=32),role:req.adminUser.role});
  if(automated){
   if(!configured())return res.status(503).json({error:"Firebase service account not configured"});
   const batchId=String(req.body?.batchId||"");
   if(!/^[a-zA-Z0-9._:-]{8,120}$/.test(batchId))return res.status(400).json({error:"Invalid batch ID"});
   const kind=action==="notify_expiry"?"expiry":"batch";
   const once=scope+kind+":"+crypto.createHash("sha256").update(batchId).digest("hex");
   const reviewCount=Math.min(999,Math.max(0,Number(req.body?.reviewCount||0)));
   if(kind==="expiry"&&reviewCount<1)return res.status(200).json({ok:true,skipped:"No expiry exceptions to notify.",sent:0});
   const title=kind==="expiry"?"HD Careers · Expiry review needed":"HD Careers · Daily jobs ready";
   const body=kind==="expiry"?reviewCount+" uncertain job listing(s) need your review. Check exact official links.":"New verified candidates are ready for your review.";
   const acquired=await redis("SET",once,"started","NX","EX",7*86400);
   if(acquired!=="OK")return res.status(200).json({duplicate:true,sent:0,failed:0});
   const ids=await redis("SMEMBERS",indexKey)||[];
   let sent=0,failed=0;
   for(const id of ids.slice(0,100)){
    const device=await readDevice(id);
    if(!device){await redis("SREM",indexKey,id);continue}
    if(device.role==="job_editor"){
     const user=await getUser(device.username);
     if(!user||!user.active){await redis("DEL",key(id));await redis("SREM",indexKey,id);continue}
    }
    try{
     const result=await deliver(device,title,body,batchId,kind);
     if(result.invalid){await redis("DEL",key(id));await redis("SREM",indexKey,id);failed++}
     else sent++;
    }catch{failed++}
   }
   await redis("SET",once,JSON.stringify({sent,failed,at:new Date().toISOString()}),"EX",7*86400);
   return res.status(200).json({sent,failed,processed:Math.min(ids.length,100)});
  }
  if(!["register","unregister","test"].includes(action))return res.status(400).json({error:"Unsupported push action."});
  const user=req.adminUser;
  const installationId=String(req.body?.installationId||"");
  const token=String(req.body?.token||"");
  if(action==="test"){
   if(!configured())return res.status(503).json({error:"Firebase service account is not yet configured."});
   const all=await redis("SMEMBERS",indexKey)||[];
   const entries=await Promise.all(all.slice(0,150).map(async id=>({id,record:await readDevice(id)})));
   const own=entries.filter(x=>x.record?.username===user.username);
   if(!own.length)return res.status(404).json({error:"Register your Pixel for notifications first."});
   let delivered=0;
   for(const item of own){
    try{const r=await deliver(item.record,"HD Careers · Test notification","Firebase push is connected to your admin app.","test");if(r.ok)delivered++}catch{}
   }
   if(!delivered)return res.status(502).json({error:"Firebase did not accept the test push."});
   await auditMutation(req,"push.test",user.username);
   return res.status(200).json({ok:true,accepted:delivered});
  }
  if(!/^[0-9a-f-]{36}$/i.test(installationId))return res.status(400).json({error:"Invalid installation ID"});
  const id=hmac(user.username,installationId);
  if(action==="unregister"){
   await redis("DEL",key(id));await redis("SREM",indexKey,id);
   return res.status(200).json({ok:true,unregistered:true});
  }
  if(token.length<20||token.length>4096)return res.status(400).json({error:"Invalid Firebase device token"});
  const record={username:user.username,role:user.role,token,updatedAt:new Date().toISOString()};
  await redis("SET",key(id),JSON.stringify(record),"EX",60*86400);
  await redis("SADD",indexKey,id);
  await auditMutation(req,"push.register",user.username);
  return res.status(200).json({ok:true,registered:true,serverConfigured:configured()});
 }catch(error){
  return res.status(Number(error.status)||503).json({error:error.status===502?"Firebase request failed.":error.message||"Push service unavailable."});
 }
}
