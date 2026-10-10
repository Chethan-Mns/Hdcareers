import crypto from "node:crypto";

const BASE = "hd:android:push:v1";
const set = (name) => String(process.env[name] || "");
export const androidConfigured = () => Boolean(
  set("UPSTASH_REDIS_REST_URL") && set("UPSTASH_REDIS_REST_TOKEN") &&
  set("FCM_PROJECT_ID") && set("FCM_SERVICE_ACCOUNT_CLIENT_EMAIL") && set("FCM_SERVICE_ACCOUNT_PRIVATE_KEY")
);
export const storageConfigured = () => Boolean(set("UPSTASH_REDIS_REST_URL") && set("UPSTASH_REDIS_REST_TOKEN"));
export async function redis(...args) {
  if(!storageConfigured()) throw Error("Private push storage not configured.");
  const response = await fetch(set("UPSTASH_REDIS_REST_URL").replace(/\/$/,""), {
    method:"POST", headers:{"Authorization":"Bearer "+set("UPSTASH_REDIS_REST_TOKEN"),"Content-Type":"application/json"},
    body:JSON.stringify(args),signal:AbortSignal.timeout(7000),cache:"no-store"
  });
  if(!response.ok) throw Error("Private push storage returned HTTP "+response.status);
  const json=await response.json();
  if(json.error) throw Error("Private push storage operation failed.");
  return json.result;
}
export const deviceKey=BASE+":devices";
export async function devices() {
  const result=await redis("HGETALL",deviceKey);
  if(!result) return [];
  const pairs=Array.isArray(result)?
    Array.from({length:Math.floor(result.length/2)},(_,i)=>[result[i*2],result[i*2+1]]):
    Object.entries(result);
  return pairs.map(([id,value])=>{try{return {id,...JSON.parse(value)}}catch{return null}}).filter(Boolean);
}
export async function registerDevice(id,token) {
  const entries=await devices();
  if(entries.length>=8&&!entries.some(x=>x.id===id)) throw Object.assign(Error("Maximum registered devices reached."),{status:429});
  await redis("HSET",deviceKey,id,JSON.stringify({token,updatedAt:new Date().toISOString()}));
}
export async function unregisterDevice(id) { await redis("HDEL",deviceKey,id); }
export async function sent(batch,id) { return Boolean(await redis("GET",BASE+":sent:"+batch+":"+id)); }
export async function markSent(batch,id) {
  await redis("SET",BASE+":sent:"+batch+":"+id,"1","EX",30*24*3600);
}
export async function acquire(batch) {
  return await redis("SET",BASE+":lock:"+batch,"1","NX","EX",90)==="OK";
}
export async function release(batch) { await redis("DEL",BASE+":lock:"+batch); }

const jwt = () => {
  const head=Buffer.from(JSON.stringify({alg:"RS256",typ:"JWT"})).toString("base64url");
  const now=Math.floor(Date.now()/1000);
  const claims=Buffer.from(JSON.stringify({
    iss:set("FCM_SERVICE_ACCOUNT_CLIENT_EMAIL"),
    scope:"https://www.googleapis.com/auth/firebase.messaging",
    aud:"https://oauth2.googleapis.com/token",iat:now,exp:now+3500
  })).toString("base64url");
  const message=head+"."+claims;
  const pem=set("FCM_SERVICE_ACCOUNT_PRIVATE_KEY").replace(/\\n/g,"\n");
  const signature=crypto.sign("RSA-SHA256",Buffer.from(message),pem).toString("base64url");
  return message+"."+signature;
};
export async function fcmAccessToken() {
  const response=await fetch("https://oauth2.googleapis.com/token",{
    method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},
    body:new URLSearchParams({"grant_type":"urn:ietf:params:oauth:grant-type:jwt-bearer",assertion:jwt()}),
    signal:AbortSignal.timeout(9000)
  });
  if(!response.ok) throw Error("Firebase OAuth token request failed: "+response.status);
  const result=await response.json();
  if(!result.access_token) throw Error("Firebase OAuth response missing access token.");
  return result.access_token;
}
export async function sendFcm(token,notification,accessToken) {
  const project=set("FCM_PROJECT_ID");
  const response=await fetch("https://fcm.googleapis.com/v1/projects/"+encodeURIComponent(project)+"/messages:send",{
    method:"POST",
    headers:{"Content-Type":"application/json","Authorization":"Bearer "+accessToken},
    body:JSON.stringify({message:{token,data:{
      title:notification.title,body:notification.body,batchId:String(notification.batchId||""),
      kind:notification.kind||"review"
    },android:{priority:"HIGH"}}}),
    signal:AbortSignal.timeout(9500)
  });
  let data={};try{data=await response.json()}catch{}
  return {ok:response.ok,code:response.status,error:data.error?.status||null};
}
export async function readReviewBatch() {
  const repo=set("ADMIN_GITHUB_REPO")||"Chethan-Mns/Hdcareers";
  const branch=set("ADMIN_GITHUB_BASE")||"main";
  const token=set("GITHUB_PUBLISH_TOKEN");
  if(!token) throw Error("Admin GitHub token is not configured.");
  const response=await fetch("https://api.github.com/repos/"+repo+
    "/contents/data/daily-review-batch.json?ref="+encodeURIComponent(branch),{
    headers:{"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json",
      "User-Agent":"HD-Careers-Android-Push"},cache:"no-store",signal:AbortSignal.timeout(10000)
  });
  if(!response.ok) throw Error("Cannot load latest review batch.");
  const file=await response.json();
  return JSON.parse(Buffer.from(String(file.content||"").replace(/\n/g,""),"base64").toString("utf8"));
}
