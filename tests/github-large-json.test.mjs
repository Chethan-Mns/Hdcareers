import test from "node:test";
import assert from "node:assert/strict";
import {decodeGitHubJSON} from "../lib/github-large-json.js";

test("small GitHub Contents API JSON reads without fetching a blob",async()=>{
  const doc={encoding:"base64",content:Buffer.from('[{"id":1}]').toString("base64")};
  const result=await decodeGitHubJSON(doc,()=>{throw Error("unexpected blob fetch")},"test.json");
  assert.deepEqual(result,[{id:1}]);
});
test("large jobs.json with encoding none is read by exact blob SHA",async()=>{
  const jobs=Array.from({length:12000},(_,i)=>({id:i,company:"Example Employer",role:"Software Engineer",
    apply:"https://example.com/careers/engineering/"+i,description:"Full job description"}));
  const raw=JSON.stringify(jobs);
  assert.ok(Buffer.byteLength(raw)>1048576);
  let shaRequested=null;
  const result=await decodeGitHubJSON({encoding:"none",content:"",sha:"sha-for-this-commit"},sha=>{
    shaRequested=sha;
    return {encoding:"base64",content:Buffer.from(raw).toString("base64")};
  },"data/jobs.json");
  assert.equal(shaRequested,"sha-for-this-commit");
  assert.equal(result.length,12000);
  assert.deepEqual(result[0],jobs[0]);
});
test("empty GitHub response never silently erases existing jobs",async()=>{
  await assert.rejects(decodeGitHubJSON({encoding:"none",content:"",sha:"sha"},async()=>({encoding:"base64",content:""}),"data/jobs.json"),/no readable file contents/);
});
test("malformed GitHub blob yields an actionable error",async()=>{
  await assert.rejects(decodeGitHubJSON({encoding:"none",sha:"sha"},async()=>({encoding:"base64",content:Buffer.from('[').toString("base64")}),"data/jobs.json"),/incomplete JSON/);
});
