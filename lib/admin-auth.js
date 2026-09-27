import crypto from "node:crypto";

export const ADMIN_COOKIE = "hd_admin_session";
const SESSION_SECONDS = 12 * 60 * 60;

function b64url(value){
  return Buffer.from(value).toString("base64url");
}

function fromB64url(value){
  return Buffer.from(value,"base64url").toString("utf8");
}

function sessionSecret(){
  return String(process.env.ADMIN_SESSION_SECRET||"");
}

function safeEqual(a,b){
  const aa=Buffer.from(String(a||""));
  const bb=Buffer.from(String(b||""));
  if(aa.length!==bb.length)return false;
  return crypto.timingSafeEqual(aa,bb);
}

export function authConfigured(){
  return Boolean(process.env.ADMIN_USERNAME&&process.env.ADMIN_PASSWORD&&process.env.ADMIN_SESSION_SECRET);
}

export function verifyAdminCredentials(username,password){
  const expectedUser=String(process.env.ADMIN_USERNAME||"").trim().toLowerCase();
  const suppliedUser=String(username||"").trim().toLowerCase();
  const expectedPassword=String(process.env.ADMIN_PASSWORD||"");
  if(!expectedUser||!expectedPassword)return false;
  return safeEqual(suppliedUser,expectedUser)&&safeEqual(password,expectedPassword);
}

export function createAdminSession(){
  const secret=sessionSecret();
  if(!secret)throw new Error("Admin session secret is not configured.");
  const payload={v:1,exp:Math.floor(Date.now()/1000)+SESSION_SECONDS,nonce:crypto.randomBytes(16).toString("hex")};
  const body=b64url(JSON.stringify(payload));
  const sig=crypto.createHmac("sha256",secret).update(body).digest("base64url");
  return body+"."+sig;
}

export function verifyAdminSession(token){
  if(!token)return false;
  const secret=sessionSecret();
  if(!secret)return false;
  const [body,sig,extra]=String(token).split(".");
  if(!body||!sig||extra)return false;
  const expected=crypto.createHmac("sha256",secret).update(body).digest("base64url");
  if(!safeEqual(sig,expected))return false;
  try{
    const payload=JSON.parse(fromB64url(body));
    return payload&&payload.v===1&&Number(payload.exp)>Math.floor(Date.now()/1000);
  }catch{return false;}
}

export function parseCookies(req){
  const header=String(req.headers.cookie||"");
  const out={};
  for(const part of header.split(";")){
    const i=part.indexOf("=");
    if(i<0)continue;
    const k=part.slice(0,i).trim();
    const v=part.slice(i+1).trim();
    if(k)out[k]=decodeURIComponent(v);
  }
  return out;
}

export function isAdminRequest(req){
  return verifyAdminSession(parseCookies(req)[ADMIN_COOKIE]);
}

export function requireAdmin(req,res){
  if(isAdminRequest(req))return true;
  res.status(401).json({error:"Authentication required."});
  return false;
}

export function setAdminCookie(res,token){
  res.setHeader("Set-Cookie",ADMIN_COOKIE+"="+encodeURIComponent(token)+"; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age="+SESSION_SECONDS);
}

export function clearAdminCookie(res){
  res.setHeader("Set-Cookie",ADMIN_COOKIE+"=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0");
}
