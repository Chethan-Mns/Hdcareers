import {requireAdmin} from "../../lib/admin-auth.js";
import {auditEntries} from "../../lib/admin-store.js";

export default async function handler(req,res){
  res.setHeader("Cache-Control","no-store");
  if(req.method!=="GET"){res.setHeader("Allow","GET");return res.status(405).json({error:"Method not allowed."});}
  if(!await requireAdmin(req,res,["owner"]))return;
  try{return res.status(200).json({items:await auditEntries(100)});}
  catch{return res.status(503).json({error:"Audit ledger unavailable."});}
}
