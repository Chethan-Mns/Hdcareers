import {requireAdmin} from "../../lib/admin-auth.js";
import {androidConfigured,registerDevice,unregisterDevice,devices,redis,fcmAccessToken,sendFcm} from "../../lib/android-notify.js";

function originAllowed(req) {
  const origin=String(req.headers.origin||"");
  if(!origin) return true;
  const host=String(req.headers["x-forwarded-host"]||req.headers.host||"").toLowerCase();
  try { return new URL(origin).host.toLowerCase()===host; } catch { return false; }
}

async function testPush(res) {
  if(await redis("SET","hd:android:test:limit","1","NX","EX",60)!=="OK")
    return res.status(429).json({error:"Wait one minute before sending another test."});
  const list=await devices();
  if(!list.length) return res.status(409).json({error:"No Android device is registered."});
  const access=await fcmAccessToken();
  const results=[];
  for(const device of list) {
    try {
      const result=await sendFcm(device.token,{kind:"test",title:"HD Careers Push Test",
        body:"Your Pixel is connected to HD Careers notifications."},access);
      if(result.error==="UNREGISTERED") await unregisterDevice(device.id);
      results.push({id:device.id,accepted:result.ok,error:result.error});
    } catch {
      results.push({id:device.id,accepted:false,error:"Delivery failed"});
    }
  }
  return res.status(200).json({ok:results.some(x=>x.accepted),results});
}

export default async function handler(req,res) {
  res.setHeader("Cache-Control","private, no-store");
  if(!["GET","POST"].includes(req.method)) return res.status(405).json({error:"Method not allowed."});
  if(!requireAdmin(req,res)) return;
  if(!originAllowed(req)) return res.status(403).json({error:"Invalid origin."});
  if(req.method==="GET") return res.status(200).json({configured:androidConfigured()});
  if(!androidConfigured()) return res.status(503).json({error:"Firebase push credentials and private storage are not yet configured."});
  try {
    if(req.body?.action==="test") return await testPush(res);
    const id=String(req.body?.installationId||"").trim();
    if(!/^[0-9a-f-]{36}$/i.test(id)) return res.status(400).json({error:"Invalid installation identifier."});
    if(req.body?.action==="unregister") {
      await unregisterDevice(id);
      return res.status(200).json({ok:true,registered:false});
    }
    if(req.body?.action!=="register") return res.status(400).json({error:"Invalid registration action."});
    const token=String(req.body?.token||"").trim();
    if(token.length<40||token.length>4096||!/^[A-Za-z0-9_:\-]+$/.test(token))
      return res.status(400).json({error:"Invalid Firebase device token."});
    await registerDevice(id,token);
    return res.status(200).json({ok:true,registered:true});
  } catch(err) {
    return res.status(err.status||502).json({error:err.message||"Firebase operation failed."});
  }
}
