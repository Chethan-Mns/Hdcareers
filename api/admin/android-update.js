import {requireAdmin} from "../../lib/admin-auth.js";

export default async function handler(req,res){
  res.setHeader("Cache-Control","private, no-store");
  if(!await requireAdmin(req,res,["owner","job_editor"]))return;
  if(req.method!=="GET"){res.setHeader("Allow","GET");return res.status(405).json({error:"Method not allowed"});}
  const versionCode=Number(process.env.HD_ANDROID_UPDATE_VERSION_CODE||0);
  const versionName=String(process.env.HD_ANDROID_UPDATE_VERSION_NAME||"");
  const apkUrl=String(process.env.HD_ANDROID_UPDATE_APK_URL||"");
  const sha256=String(process.env.HD_ANDROID_UPDATE_SHA256||"").toLowerCase();
  if(!Number.isSafeInteger(versionCode)||versionCode<1||!/^https:\/\//.test(apkUrl)||!/^[0-9a-f]{64}$/.test(sha256)){
    return res.status(200).json({available:false,reason:"No signed APK update published"});
  }
  return res.status(200).json({
    available:true,versionCode,versionName,
    apkUrl,sha256,
    notes:String(process.env.HD_ANDROID_UPDATE_NOTES||"HD Careers improvements").slice(0,500)
  });
}
