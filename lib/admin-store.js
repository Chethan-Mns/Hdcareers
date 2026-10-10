import crypto from "node:crypto";

const prefix="hdadmin:v2:"+(process.env.VERCEL_ENV==="preview"?"preview:":"production:");
const configured=()=>Boolean(process.env.HD_ADMIN_REDIS_URL&&process.env.HD_ADMIN_REDIS_TOKEN);
export function storeConfigured(){return configured();}

export async function redis(...command){
  if(!configured())throw new Error("HD Careers secure user store is not configured.");
  const raw=String(process.env.HD_ADMIN_REDIS_URL).replace(/\/$/,"");
  const url=new URL(raw);
  if(url.protocol!=="https:"||!url.hostname)throw new Error("Secure HTTPS Redis endpoint required.");
  const response=await fetch(url.toString(),{
    method:"POST",
    headers:{Authorization:"Bearer "+process.env.HD_ADMIN_REDIS_TOKEN,"Content-Type":"application/json"},
    body:JSON.stringify(command),
    signal:AbortSignal.timeout(8000)
  });
  if(!response.ok)throw new Error("HD Careers user store unavailable ("+response.status+").");
  const data=await response.json();
  if(data.error)throw new Error("HD Careers user store rejected an operation.");
  return data.result;
}

export function normalizeUsername(value){
  const text=String(value||"").trim().toLowerCase();
  return /^[a-z][a-z0-9._-]{2,39}$/.test(text)?text:"";
}

const userKey=name=>prefix+"user:"+name;
const revisionKey=name=>prefix+"revision:"+name;
const sessionKey=token=>prefix+"session:"+crypto.createHmac("sha256",String(process.env.ADMIN_SESSION_SECRET||"")).update(token).digest("hex");
export const SESSION_SECONDS=12*60*60;

export async function getUser(name){
  const username=normalizeUsername(name);
  if(!username)return null;
  const value=await redis("GET",userKey(username));
  if(!value)return null;
  try{return JSON.parse(value);}catch{throw new Error("Corrupted user record.");}
}

export function hashPassword(password){
  const p=String(password||"");
  if(p.length<14||p.length>128)throw new Error("Password must be 14–128 characters.");
  const salt=crypto.randomBytes(16).toString("hex");
  const digest=crypto.scryptSync(p,Buffer.from(salt,"hex"),64,{N:16384,r:8,p:1}).toString("hex");
  return {salt,digest,algorithm:"scrypt-16384"};
}

export function matchesPassword(password,record){
  if(!record||record.algorithm!=="scrypt-16384"||!record.salt||!record.digest)return false;
  try{
    const actual=crypto.scryptSync(String(password||""),Buffer.from(record.salt,"hex"),64,{N:16384,r:8,p:1});
    const expected=Buffer.from(record.digest,"hex");
    return actual.length===expected.length&&crypto.timingSafeEqual(actual,expected);
  }catch{return false;}
}

export async function createEditor(username,password,actor){
  const name=normalizeUsername(username);
  if(!name)throw new Error("Username must be 3–40 letters, digits, dots, hyphens or underscores and begin with a letter.");
  if(name===String(process.env.ADMIN_USERNAME||"").trim().toLowerCase())throw new Error("Owner account cannot be overwritten.");
  const record={username:name,role:"job_editor",active:true,createdAt:new Date().toISOString(),createdBy:actor,...hashPassword(password)};
  const result=await redis("SET",userKey(name),JSON.stringify(record),"NX");
  if(result!=="OK")throw Object.assign(new Error("Username is already registered."),{status:409});
  await redis("SADD",prefix+"users",name);
  return {username:name,role:record.role,active:true,createdAt:record.createdAt};
}

export async function listEditors(){
  const names=await redis("SMEMBERS",prefix+"users")||[];
  const users=await Promise.all(names.map(getUser));
  return users.filter(Boolean).map(({username,role,active,createdAt,createdBy})=>({username,role,active,createdAt,createdBy})).sort((a,b)=>a.username.localeCompare(b.username));
}

export async function setEditorState(username,action,password){
  const name=normalizeUsername(username);
  if(!name||name===normalizeUsername(process.env.ADMIN_USERNAME))throw new Error("Owner account cannot be modified here.");
  const record=await getUser(name);
  if(!record||record.role!=="job_editor")throw Object.assign(new Error("Job Editor not found."),{status:404});
  if(action==="disable")record.active=false;
  else if(action==="enable")record.active=true;
  else if(action==="reset_password")Object.assign(record,hashPassword(password));
  else if(action!=="revoke_sessions")throw Object.assign(new Error("Invalid user action."),{status:400});
  await redis("INCR",revisionKey(name));
  if(action!=="revoke_sessions"){
    record.updatedAt=new Date().toISOString();
    await redis("SET",userKey(name),JSON.stringify(record));
  }
  return {username:name,role:"job_editor",active:record.active,action};
}

export async function revision(username){return Number(await redis("GET",revisionKey(username))||0);}

export async function issueSession(username,role){
  if(!["owner","job_editor"].includes(role))throw new Error("Unsupported account role.");
  const token="v2."+crypto.randomBytes(32).toString("base64url");
  const record={username,role,revision:await revision(username),issuedAt:Date.now()};
  await redis("SET",sessionKey(token),JSON.stringify(record),"EX",SESSION_SECONDS);
  return token;
}

export async function lookupSession(token){
  if(!/^v2\.[A-Za-z0-9_-]{40,60}$/.test(String(token||"")))return null;
  const text=await redis("GET",sessionKey(token));
  if(!text)return null;
  const s=JSON.parse(text);
  if(s.role!=="owner"&&s.role!=="job_editor")return null;
  if(s.revision!==await revision(s.username))return null;
  if(s.role==="owner"){
    if(s.username!==String(process.env.ADMIN_USERNAME||"").trim().toLowerCase())return null;
  }else{
    const user=await getUser(s.username);
    if(!user||user.role!==s.role||!user.active)return null;
  }
  return {username:s.username,role:s.role};
}

export async function removeSession(token){
  if(/^v2\.[A-Za-z0-9_-]{40,60}$/.test(String(token||"")))await redis("DEL",sessionKey(token));
}

export async function audit(event){
  const entry={at:new Date().toISOString(),username:String(event.username||"unknown").slice(0,50),role:String(event.role||"").slice(0,30),action:String(event.action||"").slice(0,100),target:String(event.target||"").slice(0,160),result:String(event.result||"attempt").slice(0,40)};
  await redis("LPUSH",prefix+"audit",JSON.stringify(entry));
  await redis("LTRIM",prefix+"audit",0,999);
  return entry;
}

export async function auditEntries(limit=100){
  const values=await redis("LRANGE",prefix+"audit",0,Math.min(200,Math.max(1,limit))-1)||[];
  return values.map(value=>JSON.parse(value));
}

export async function loginAllowed(username,ip){
  const id=crypto.createHash("sha256").update(normalizeUsername(username)+"|"+String(ip||"unknown").slice(0,150)).digest("hex");
  const key=prefix+"attempt:"+id;
  const count=Number(await redis("INCR",key));
  if(count===1)await redis("EXPIRE",key,900);
  return count<=8;
}
