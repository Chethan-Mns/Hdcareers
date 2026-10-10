import {requireAdmin,auditMutation} from "../../lib/admin-auth.js";
import {audit,createEditor,listEditors,normalizeUsername,setEditorState} from "../../lib/admin-store.js";

function safeOrigin(req){
  if(req.headers["sec-fetch-site"]==="cross-site")return false;
  const origin=String(req.headers.origin||"");
  if(!origin)return true;
  const host=String(req.headers["x-forwarded-host"]||req.headers.host||"").toLowerCase();
  try{return new URL(origin).host.toLowerCase()===host;}catch{return false;}
}

export default async function handler(req,res){
  res.setHeader("Cache-Control","no-store");
  if(!["GET","POST"].includes(req.method)){res.setHeader("Allow","GET, POST");return res.status(405).json({error:"Method not allowed."});}
  if(!await requireAdmin(req,res,["owner"]))return;
  if(req.method==="POST"&&!safeOrigin(req))return res.status(403).json({error:"Invalid request origin."});
  try{
    if(req.method==="GET")return res.status(200).json({
      owner:{username:normalizeUsername(process.env.ADMIN_USERNAME),role:"owner",active:true},
      editors:await listEditors()
    });
    const action=String(req.body?.action||"");
    const username=normalizeUsername(req.body?.username);
    if(!username)return res.status(400).json({error:"A valid username is required."});
    if(!["create","disable","enable","reset_password","revoke_sessions"].includes(action)){
      return res.status(400).json({error:"Unsupported account action."});
    }
    if(action==="create"||action==="reset_password"){
      const password=String(req.body?.password||"");
      if(password.length<14||password.length>128)return res.status(400).json({error:"Password must contain 14–128 characters."});
    }
    await auditMutation(req,"account."+action,username);
    const user=action==="create"
      ?await createEditor(username,req.body.password,req.adminUser.username)
      :await setEditorState(username,action,req.body.password);
    await audit({...req.adminUser,action:"account."+action,target:username,result:"success"});
    return res.status(200).json({ok:true,editor:user});
  }catch(error){
    const clientError=[400,404,409].includes(error.status)||/Username|Password|Owner account|Job Editor not found|Invalid user action/.test(error.message||"");
    return res.status(clientError?(error.status||400):503).json({error:clientError?error.message:"Secure account service unavailable."});
  }
}
