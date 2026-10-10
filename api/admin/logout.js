import {clearAdminCookie,getAdminIdentity,revokeRequestSession} from "../../lib/admin-auth.js";
import {audit} from "../../lib/admin-store.js";

export default async function handler(req,res){
  res.setHeader("Cache-Control","no-store");
  if(req.method!=="POST"){res.setHeader("Allow","POST");return res.status(405).json({error:"Method not allowed."});}
  if(req.headers["sec-fetch-site"]==="cross-site")return res.status(403).json({error:"Invalid request origin."});
  try{
    const user=await getAdminIdentity(req);
    if(user){
      await audit({...user,action:"logout",result:"success"});
      await revokeRequestSession(req);
    }
    clearAdminCookie(res);
    return res.status(200).json({ok:true});
  }catch{
    clearAdminCookie(res);
    return res.status(503).json({error:"Could not confirm server-side revocation. Contact the Owner if needed."});
  }
}
