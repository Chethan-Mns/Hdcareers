import {requireAdmin} from "../../lib/admin-auth.js";
import {androidConfigured,devices,redis,fcmAccessToken,sendFcm,unregisterDevice} from "../../lib/android-notify.js";
export default async function handler(req,res) {
  res.setHeader("Cache-Control","private, no-store");
  if(req.method!=="POST")return res.status(405).json({error:"Method not allowed."});
  if(!requireAdmin(req,res))return;
  const origin=String(req.headers.origin||"");
  if(origin){try{if(new URL(origin).host!==String(req.headers["x-forwarded-host"]||req.headers.host))
    return res.status(403).json({error:"Invalid origin."})}catch{return res.status(403).json({error:"Invalid origin."})}}
  if(!androidConfigured())return res.status(503).json({error:"Firebase server credentials are not configured."});
  try{
    if(await redis("SET","hd:android:test:limit","1","NX","EX",60)!=="OK")
      return res.status(429).json({error:"Wait one minute before sending another test."});
    const list=await devices();
    if(!list.length)return res.status(409).json({error:"No Android device is registered."});
    const access=await fcmAccessToken();
    const results=[];
    for(const device of list){
      const r=await sendFcm(device.token,{kind:"test",title:"HD Careers Push Test",
        body:"Your Pixel is connected to HD Careers notifications."},access);
      if(r.error==="UNREGISTERED")await unregisterDevice(device.id);
      results.push({id:device.id,accepted:r.ok,error:r.error});
    }
    return res.status(200).json({ok:results.some(x=>x.accepted),results});
  }catch{return res.status(502).json({error:"Android push delivery test failed."})}
}
