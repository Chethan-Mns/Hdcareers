import {getAdminIdentity} from "../../lib/admin-auth.js";
import teamHandler from "../../lib/admin-team-handler.js";
import auditHandler from "../../lib/admin-audit-handler.js";
import passwordHandler from "../../lib/admin-password-handler.js";

export default async function handler(req,res){
  res.setHeader("Cache-Control","no-store");
  // Consolidate all Owner-only account operations into an existing serverless
  // endpoint; Vercel rewrites map /api/admin/{team,audit,owner-password} here.
  // Each operation still enforces its own explicit RBAC check server-side.
  const operation=String(req.query?.adminOperation||"");
  if(operation==="team")return teamHandler(req,res);
  if(operation==="audit")return auditHandler(req,res);
  if(operation==="owner-password")return passwordHandler(req,res);
  if(req.method!=="GET"){res.setHeader("Allow","GET");return res.status(405).json({error:"Method not allowed."});}
  try{
    const user=await getAdminIdentity(req);
    return res.status(200).json({authenticated:Boolean(user),username:user?.username||null,role:user?.role||null});
  }catch{
    return res.status(503).json({error:"Secure session service unavailable.",authenticated:false});
  }
}
