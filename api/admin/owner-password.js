import {requireAdmin,verifyCredentials,auditMutation,clearAdminCookie} from "../../lib/admin-auth.js";
import {changeOwnerPassword,audit,loginAllowed} from "../../lib/admin-store.js";

function safeOrigin(req){
  if(req.headers["sec-fetch-site"]==="cross-site")return false;
  const origin=String(req.headers.origin||"");
  if(!origin)return true;
  const host=String(req.headers["x-forwarded-host"]||req.headers.host||"").toLowerCase();
  try{return new URL(origin).host.toLowerCase()===host}catch{return false}
}

export default async function handler(req,res){
  res.setHeader("Cache-Control","no-store");
  if(req.method!=="POST"){
    res.setHeader("Allow","POST");
    return res.status(405).json({error:"Method not allowed."});
  }
  if(!await requireAdmin(req,res,["owner"]))return;
  if(!safeOrigin(req))return res.status(403).json({error:"Invalid request origin."});

  const currentPassword=String(req.body?.currentPassword||"");
  const newPassword=String(req.body?.newPassword||"");
  if(!currentPassword||currentPassword.length>128||newPassword.length<14||newPassword.length>128){
    return res.status(400).json({error:"Enter your current password and a new password of 14–128 characters."});
  }
  if(currentPassword===newPassword)return res.status(400).json({error:"Choose a different password."});

  const identity=req.adminUser;
  const ip=String(req.headers["x-vercel-forwarded-for"]||req.headers["x-forwarded-for"]||req.socket?.remoteAddress||"unknown").split(",")[0];
  try{
    if(!await loginAllowed(identity.username,ip)){
      res.setHeader("Retry-After","900");
      return res.status(429).json({error:"Too many password attempts. Please try again later."});
    }
    const verified=await verifyCredentials(identity.username,currentPassword);
    if(!verified||verified.role!=="owner"){
      await audit({...identity,action:"owner.password.change",target:"owner",result:"denied"});
      return res.status(403).json({error:"Current password is incorrect."});
    }
    await auditMutation(req,"owner.password.change","owner");
    await changeOwnerPassword(newPassword);
    clearAdminCookie(res);
    // An attempted change was already audited. A post-change audit failure
    // must not conceal a successful password rotation from the Owner.
    try{await audit({...identity,action:"owner.password.change",target:"owner",result:"success"});}catch{}
    return res.status(200).json({ok:true,message:"Owner password changed. All Owner sessions have been signed out. Sign in again."});
  }catch{
    return res.status(503).json({error:"Could not update your password securely. Please try again."});
  }
}
