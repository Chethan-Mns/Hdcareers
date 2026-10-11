// Test-only mock for the Redis REST commands exercised by RBAC-protected APIs.
export function createFakeRedis(){
  const store=new Map();
  const url="https://hd-test-redis.invalid";
  function response(target,options={}){
    if(!String(target).startsWith(url))return null;
    const [op,key,...args]=JSON.parse(options.body);
    let result=null;
    if(op==="GET")result=store.get(key)??null;
    if(op==="SET"){if(!args.includes("NX")||!store.has(key)){store.set(key,args[0]);result="OK";}}
    if(op==="DEL")result=store.delete(key)?1:0;
    if(op==="INCR"){result=Number(store.get(key)||0)+1;store.set(key,String(result));}
    if(op==="EXPIRE")result=1;
    if(op==="SADD"){const names=store.get(key)||[];if(!names.includes(args[0]))names.push(args[0]);store.set(key,names);result=1;}
    if(op==="SMEMBERS")result=store.get(key)||[];
    if(op==="LPUSH"){const values=store.get(key)||[];values.unshift(args[0]);store.set(key,values);result=values.length;}
    if(op==="LRANGE")result=(store.get(key)||[]).slice(0,args[1]+1);
    if(op==="LTRIM"){const values=store.get(key)||[];store.set(key,values.slice(0,args[1]+1));result="OK";}
    if(!["GET","SET","DEL","INCR","EXPIRE","SADD","SMEMBERS","LPUSH","LRANGE","LTRIM"].includes(op))throw Error("Unexpected Redis mock op: "+op);
    return {ok:true,status:200,json:async()=>({result})};
  }
  return {url,store,response};
}
