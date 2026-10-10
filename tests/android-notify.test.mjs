import test from "node:test";
import assert from "node:assert/strict";
import crypto from "node:crypto";
import {androidConfigured,storageConfigured,redis,registerDevice,devices,fcmAccessToken,sendFcm} from "../lib/android-notify.js";
import deviceHandler from "../api/admin/android-devices.js";
import dispatchHandler from "../api/notifications/android-dispatch.js";

function res(){return {statusCode:200,body:null,setHeader(){return this},status(x){this.statusCode=x;return this},json(x){this.body=x;return this}}}
test("unconfigured Firebase and Redis do not report operational notifications",()=>{
  assert.equal(androidConfigured(),false);
  assert.equal(storageConfigured(),false);
});
test("Android device token endpoint requires admin auth",async()=>{
  const response=res();
  await deviceHandler({method:"POST",headers:{},body:{action:"register"}},response);
  assert.equal(response.statusCode,401);
});
test("notification webhook refuses unauthenticated triggers",async()=>{
  const response=res();
  await dispatchHandler({method:"POST",headers:{}},response);
  assert.equal(response.statusCode,401);
});
test("device storage stays behind the authenticated private Redis API",async()=>{
  const old=globalThis.fetch, url=process.env.UPSTASH_REDIS_REST_URL,token=process.env.UPSTASH_REDIS_REST_TOKEN;
  const commands=[];
  try{
    process.env.UPSTASH_REDIS_REST_URL="https://unit-test.upstash.io";
    process.env.UPSTASH_REDIS_REST_TOKEN="test-private-token";
    globalThis.fetch=async(_url,opts)=>{
      assert.equal(opts.headers.Authorization,"Bearer test-private-token");
      const cmd=JSON.parse(opts.body);commands.push(cmd);
      return {ok:true,json:async()=>({result:cmd[0]==="HGETALL"?["device",JSON.stringify({token:"test-token"})]:1})};
    };
    await registerDevice("device","test-token");
    assert.deepEqual(commands.slice(0,2).map(x=>x[0]),["HGETALL","HSET"]);
    const items=await devices();
    assert.equal(items[0].token,"test-token");
  }finally{
    globalThis.fetch=old;
    if(url===undefined)delete process.env.UPSTASH_REDIS_REST_URL;else process.env.UPSTASH_REDIS_REST_URL=url;
    if(token===undefined)delete process.env.UPSTASH_REDIS_REST_TOKEN;else process.env.UPSTASH_REDIS_REST_TOKEN=token;
  }
});
test("Firebase OAuth assertion is RSA signed and FCM uses auth token",async()=>{
  const {publicKey,privateKey}=crypto.generateKeyPairSync("rsa",{modulusLength:2048});
  const values=["FCM_SERVICE_ACCOUNT_CLIENT_EMAIL","FCM_SERVICE_ACCOUNT_PRIVATE_KEY","FCM_PROJECT_ID"];
  const original=values.map(v=>process.env[v]);const old=globalThis.fetch;
  try{
    process.env.FCM_SERVICE_ACCOUNT_CLIENT_EMAIL="service@unit.test";
    process.env.FCM_SERVICE_ACCOUNT_PRIVATE_KEY=privateKey.export({format:"pem",type:"pkcs8"}).toString();
    process.env.FCM_PROJECT_ID="test-project";
    globalThis.fetch=async(url,opts)=>{
      if(String(url).includes("oauth2.googleapis.com")){
        const params=new URLSearchParams(opts.body);
        const jwt=params.get("assertion");const [head,body,sig]=jwt.split(".");
        assert.equal(JSON.parse(Buffer.from(head,"base64url").toString()).alg,"RS256");
        assert.equal(JSON.parse(Buffer.from(body,"base64url").toString()).iss,"service@unit.test");
        assert.ok(crypto.verify("RSA-SHA256",Buffer.from(head+"."+body),publicKey,Buffer.from(sig,"base64url")));
        return {ok:true,json:async()=>({access_token:"test-access"})};
      }
      assert.ok(String(url).includes("projects/test-project/messages:send"));
      assert.equal(opts.headers.Authorization,"Bearer test-access");
      const message=JSON.parse(opts.body).message;
      assert.equal(message.token,"sample-device-token");
      return {ok:true,status:200,json:async()=>({name:"projects/test-project/messages/123"})};
    };
    const access=await fcmAccessToken();
    assert.equal(access,"test-access");
    const result=await sendFcm("sample-device-token",{title:"Jobs ready",body:"Review now",batchId:"test"},access);
    assert.equal(result.ok,true);
  }finally{
    globalThis.fetch=old;
    values.forEach((v,i)=>{if(original[i]===undefined)delete process.env[v];else process.env[v]=original[i]});
  }
});
