import {getAdminIdentity} from "../../lib/admin-auth.js";

export default async function handler(req,res){
  res.setHeader("Cache-Control","no-store");
  if(req.method!=="GET"){res.setHeader("Allow","GET");return res.status(405).json({error:"Method not allowed."});}
  try{
    const user=await getAdminIdentity(req);
    return res.status(200).json({authenticated:Boolean(user),username:user?.username||null,role:user?.role||null});
  }catch{
    return res.status(503).json({error:"Secure session service unavailable.",authenticated:false});
  }
}
