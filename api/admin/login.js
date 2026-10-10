import {authConfigured,createAdminSession,setAdminCookie,verifyCredentials} from "../../lib/admin-auth.js";
import {audit,loginAllowed} from "../../lib/admin-store.js";

export default async function handler(req,res){
  res.setHeader("Cache-Control","no-store");
  if(req.method!=="POST"){res.setHeader("Allow","POST");return res.status(405).json({error:"Method not allowed."});}
  if(!authConfigured())return res.status(503).json({error:"Secure admin authentication is not configured."});
  const username=String(req.body?.username||"");
  const password=String(req.body?.password||"");
  const ip=String(req.headers["x-vercel-forwarded-for"]||req.headers["x-forwarded-for"]||req.socket?.remoteAddress||"unknown").split(",")[0];
  try{
    if(!await loginAllowed(username,ip)){
      res.setHeader("Retry-After","900");
      return res.status(429).json({error:"Too many attempts. Please try again later."});
    }
    const user=await verifyCredentials(username,password);
    if(!user){
      await audit({username,role:"",action:"login",result:"denied"});
      return res.status(401).json({error:"Invalid username or password."});
    }
    await audit({...user,action:"login",result:"success"});
    const token=await createAdminSession(user);
    setAdminCookie(res,token);
    return res.status(200).json({ok:true,authenticated:true,username:user.username,role:user.role});
  }catch{
    return res.status(503).json({error:"Secure admin sign-in temporarily unavailable."});
  }
}
