import {authConfigured,createAdminSession,setAdminCookie,verifyAdminCredentials} from "../../lib/admin-auth.js";

const attempts=new Map();
const WINDOW_MS=10*60*1000;
const LOCK_MS=15*60*1000;
const MAX_ATTEMPTS=5;

function clientKey(req){
  const forwarded=String(req.headers["x-forwarded-for"]||"").split(",")[0].trim();
  return forwarded||String(req.socket&&req.socket.remoteAddress||"unknown");
}

function stateFor(key){
  const now=Date.now();
  const current=attempts.get(key);
  if(!current||now-current.first>WINDOW_MS){
    const next={count:0,first:now,lockedUntil:0};
    attempts.set(key,next);
    return next;
  }
  return current;
}

export default async function handler(req,res){
  res.setHeader("Cache-Control","no-store");
  if(req.method!=="POST"){
    res.setHeader("Allow","POST");
    return res.status(405).json({error:"Method not allowed."});
  }
  if(!authConfigured())return res.status(503).json({error:"Admin authentication is not configured in Vercel."});

  const key=clientKey(req);
  const state=stateFor(key);
  const now=Date.now();
  if(state.lockedUntil>now){
    const seconds=Math.ceil((state.lockedUntil-now)/1000);
    res.setHeader("Retry-After",String(seconds));
    return res.status(429).json({error:"Too many failed attempts. Try again later."});
  }

  const username=String(req.body&&req.body.username||"");
  const password=String(req.body&&req.body.password||"");
  if(!username||!password||!verifyAdminCredentials(username,password)){
    state.count++;
    if(state.count>=MAX_ATTEMPTS)state.lockedUntil=now+LOCK_MS;
    attempts.set(key,state);
    return res.status(401).json({error:"Invalid username or password."});
  }

  attempts.delete(key);
  const token=createAdminSession();
  setAdminCookie(res,token);
  return res.status(200).json({ok:true,authenticated:true});
}
