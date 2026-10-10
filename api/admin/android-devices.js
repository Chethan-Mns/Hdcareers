import {requireAdmin} from "../../lib/admin-auth.js";
import {androidConfigured,storageConfigured,registerDevice,unregisterDevice} from "../../lib/android-notify.js";
function originAllowed(req) {
  const origin=String(req.headers.origin||"");
  if(!origin) return true;
  const host=String(req.headers["x-forwarded-host"]||req.headers.host||"").toLowerCase();
  try{return new URL(origin).host.toLowerCase()===host}catch{return false}
}
export default async function handler(req,res){
  res.setHeader("Cache-Control","private, no-store");
  if(!["GET","POST"].includes(req.method)) return res.status(405).json({error:"Method not allowed."});
  if(!requireAdmin(req,res))return;
  if(!originAllowed(req))return res.status(403).json({error:"Invalid origin."});
  if(req.method==="GET")return res.status(200).json({configured:androidConfigured()});
  if(!androidConfigured())return res.status(503).json({error:"Firebase push credentials and private storage are not yet configured."});
  const id=String(req.body?.installationId||"").trim();
  if(!/^[0-9a-f-]{36}$/i.test(id))return res.status(400).json({error:"Invalid installation identifier."});
  try{
    if(req.body?.action==="unregister"){
      await unregisterDevice(id);
      return res.status(200).json({ok:true,registered:false});
    }
    if(req.body?.action!=="register")return res.status(400).json({error:"Invalid registration action."});
    const token=String(req.body?.token||"").trim();
    if(token.length<40||token.length>4096||!/^[A-Za-z0-9_:\-]+$/.test(token))
      return res.status(400).json({error:"Invalid Firebase device token."});
    await registerDevice(id,token);
    return res.status(200).json({ok:true,registered:true});
  }catch(err){return res.status(err.status||502).json({error:err.message||"Push registration failed."})}
}
