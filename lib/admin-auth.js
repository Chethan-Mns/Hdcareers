import crypto from "node:crypto";
import {storeConfigured,getUser,matchesPassword,issueSession,lookupSession,removeSession,normalizeUsername,SESSION_SECONDS,audit} from "./admin-store.js";

export const ADMIN_COOKIE="hd_admin_session";

function safeEqual(a,b){
  const aa=Buffer.from(String(a||""));
  const bb=Buffer.from(String(b||""));
  return aa.length===bb.length&&crypto.timingSafeEqual(aa,bb);
}

export function authConfigured(){
  return Boolean(process.env.ADMIN_USERNAME&&process.env.ADMIN_PASSWORD&&process.env.ADMIN_SESSION_SECRET&&storeConfigured());
}

export function verifyAdminCredentials(username,password){
  const owner=normalizeUsername(process.env.ADMIN_USERNAME);
  return Boolean(owner&&process.env.ADMIN_PASSWORD&&safeEqual(normalizeUsername(username),owner)&&safeEqual(password,process.env.ADMIN_PASSWORD));
}

export async function verifyCredentials(username,password){
  const name=normalizeUsername(username);
  if(!name||!password)return null;
  if(name===normalizeUsername(process.env.ADMIN_USERNAME)){
    return verifyAdminCredentials(name,password)?{username:name,role:"owner"}:null;
  }
  const user=await getUser(name);
  if(!user||!user.active||user.role!=="job_editor"||!matchesPassword(password,user))return null;
  return {username:name,role:"job_editor"};
}

export async function createAdminSession(identity){
  if(!identity||!identity.username||!identity.role)throw new Error("Authenticated identity required.");
  return issueSession(identity.username,identity.role);
}

export function parseCookies(req){
  const out={};
  for(const part of String(req?.headers?.cookie||"").split(";")){
    const i=part.indexOf("=");
    if(i<0)continue;
    const key=part.slice(0,i).trim();
    try{if(key)out[key]=decodeURIComponent(part.slice(i+1).trim());}catch{}
  }
  return out;
}

export function sessionToken(req){
  const auth=String(req?.headers?.authorization||"");
  const bearer=auth.startsWith("Bearer ")?auth.slice(7).trim():"";
  return bearer||parseCookies(req)[ADMIN_COOKIE]||"";
}

export async function getAdminIdentity(req){
  if(req.adminUser)return req.adminUser;
  const user=await lookupSession(sessionToken(req));
  if(user)req.adminUser=user;
  return user;
}

export async function verifyAdminSession(token){return Boolean(await lookupSession(token));}
export async function isAdminRequest(req){return Boolean(await getAdminIdentity(req));}

export async function requireAdmin(req,res,roles=["owner","job_editor"]){
  let user;
  try{user=await getAdminIdentity(req);}
  catch{return res.status(503).json({error:"Secure admin session service unavailable."}),false;}
  if(!user)return res.status(401).json({error:"Authentication required."}),false;
  if(!roles.includes(user.role))return res.status(403).json({error:"Your account does not have permission for this operation."}),false;
  return true;
}

export async function auditMutation(req,action,target){
  if(!req.adminUser)throw new Error("An authenticated account is required for auditing.");
  return audit({...req.adminUser,action,target,result:"attempt"});
}

export async function revokeRequestSession(req){
  await removeSession(sessionToken(req));
}

export function setAdminCookie(res,token){
  res.setHeader("Set-Cookie",ADMIN_COOKIE+"="+encodeURIComponent(token)+"; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age="+SESSION_SECONDS);
}

export function clearAdminCookie(res){
  res.setHeader("Set-Cookie",ADMIN_COOKIE+"=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0");
}
