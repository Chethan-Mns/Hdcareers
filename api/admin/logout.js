import {clearAdminCookie} from "../../lib/admin-auth.js";

export default async function handler(req,res){
  res.setHeader("Cache-Control","no-store");
  if(req.method!=="POST"){
    res.setHeader("Allow","POST");
    return res.status(405).json({error:"Method not allowed."});
  }
  clearAdminCookie(res);
  return res.status(200).json({ok:true});
}
