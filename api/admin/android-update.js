import {requireAdmin} from "../../lib/admin-auth.js";
import {createHmac,createHash} from "node:crypto";

function hexSha256(value){return createHash("sha256").update(value).digest("hex");}
function hmac(key,value,encoding){return createHmac("sha256",key).update(value).digest(encoding);}
function signedGet(key){
  const account=process.env.HD_R2_ACCOUNT_ID;
  const bucket=process.env.HD_R2_BUCKET;
  const access=process.env.HD_R2_ACCESS_KEY_ID;
  const secret=process.env.HD_R2_SECRET_ACCESS_KEY;
  if(!account||!bucket||!access||!secret)return null;
  const host=account+".r2.cloudflarestorage.com";
  const uri="/"+bucket+"/"+key.split("/").map(encodeURIComponent).join("/");
  const now=new Date();
  const stamp=now.toISOString().replace(/[:-]|\.\d{3}/g,"").slice(0,15)+"Z";
  const date=stamp.slice(0,8);
  const scope=date+"/auto/s3/aws4_request";
  const params=new URLSearchParams({
    "X-Amz-Algorithm":"AWS4-HMAC-SHA256",
    "X-Amz-Credential":access+"/"+scope,
    "X-Amz-Date":stamp,
    "X-Amz-Expires":"180",
    "X-Amz-SignedHeaders":"host"
  });
  params.sort();
  const canonical="GET\n"+uri+"\n"+params.toString().replace(/%7E/g,"~")+"\nhost:"+host+"\n\nhost\nUNSIGNED-PAYLOAD";
  const stringToSign="AWS4-HMAC-SHA256\n"+stamp+"\n"+scope+"\n"+hexSha256(canonical);
  const kDate=hmac("AWS4"+secret,date);
  const kRegion=hmac(kDate,"auto");
  const kService=hmac(kRegion,"s3");
  const kSigning=hmac(kService,"aws4_request");
  const signature=hmac(kSigning,stringToSign,"hex");
  return "https://"+host+uri+"?"+params.toString()+"&X-Amz-Signature="+signature;
}
export default async function handler(req,res){
  res.setHeader("Cache-Control","private, no-store");
  if(!await requireAdmin(req,res,["owner","job_editor"]))return;
  if(req.method!=="GET"){res.setHeader("Allow","GET");return res.status(405).json({error:"Method not allowed"});}
  const versionCode=Number(process.env.HD_ANDROID_UPDATE_VERSION_CODE||0);
  const versionName=String(process.env.HD_ANDROID_UPDATE_VERSION_NAME||"");
  const sha256=String(process.env.HD_ANDROID_UPDATE_SHA256||"").toLowerCase();
  const key=String(process.env.HD_ANDROID_UPDATE_OBJECT_KEY||"");
  if(!Number.isSafeInteger(versionCode)||versionCode<1||!/^[0-9a-f]{64}$/.test(sha256)||!/^hdcareers\/android\/[A-Za-z0-9._/-]+\.apk$/.test(key)){
    return res.status(200).json({available:false,reason:"No verified private APK published"});
  }
  const apkUrl=signedGet(key);
  if(!apkUrl)return res.status(200).json({available:false,reason:"Private release storage is not configured"});
  return res.status(200).json({
    available:true,versionCode,versionName,apkUrl,sha256,
    notes:String(process.env.HD_ANDROID_UPDATE_NOTES||"HD Careers improvements").slice(0,500)
  });
}
