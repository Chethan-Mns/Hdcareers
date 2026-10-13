import test from "node:test";
import assert from "node:assert/strict";
import {attachReviewedProof} from "../lib/review-publish-proof.js";

const url="https://careers.ey.com/ey/job/Test/123456789/";
const reviewedAt="2026-10-13T04:07:36.484Z";
function batch(){
 return {status:"reviewing",priority:[{id:"ey-1",company:"EY",apply:url,reviewedStatus:"live",reviewedAt,job:{company:"EY",role:"Analyst",apply:url,status:"active",manualLiveVerifiedAt:reviewedAt}}],backup:[]};
}
test("Exact owner Live review timestamp survives canonicalization into publishing payload",()=>{
 const result=attachReviewedProof([{company:"EY",role:"Analyst",apply:url,status:"active"}],batch(),["ey-1"]);
 assert.equal(result[0].manualLiveVerifiedAt,reviewedAt);
 assert.equal(result[0].manualLiveVerifiedUrl,url);
});
test("Rejects changed URL, missing approval, expired decision and caller-submitted stale batch",()=>{
 const r=batch();r.priority[0].apply="https://careers.ey.com/ey/job/Different/123456789/";
 assert.throws(()=>attachReviewedProof([{apply:url}],r,["ey-1"]),/Reviewed official URL/);
 const expired=batch();expired.priority[0].reviewedStatus="expired";
 assert.throws(()=>attachReviewedProof([{apply:url}],expired,["ey-1"]),/Live review/);
 const stale=batch();stale.status="submitted";
 assert.throws(()=>attachReviewedProof([{apply:url}],stale,["ey-1"]),/selection has changed/);
});
test("Never copies caller-supplied verification evidence and accepts only saved exact timestamps",()=>{
 const old="2024-01-01T00:00:00Z";
 const clean=attachReviewedProof([{apply:url,manualLiveVerifiedAt:old,manualLiveVerifiedUrl:"https://fake.example"}],batch(),["ey-1"])[0];
 assert.equal(clean.manualLiveVerifiedAt,reviewedAt);
 assert.equal(clean.manualLiveVerifiedUrl,url);
 const changed=batch();changed.priority[0].job.manualLiveVerifiedAt=old;
 assert.throws(()=>attachReviewedProof([{apply:url}],changed,["ey-1"]),/timestamp changed/);
});
