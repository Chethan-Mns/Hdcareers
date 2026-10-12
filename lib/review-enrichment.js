import {employerKey,completeJob} from "./review-rules.js";

const normalizeRole=value=>String(value||"").toLowerCase().replace(/[^a-z0-9]+/g," ").trim();
const normalizeUrl=value=>{
  try { const u=new URL(value);u.hash="";const url=u.href;return (url.endsWith("/")?url.slice(0,-1):url).toLowerCase(); }
  catch { return ""; }
};
export function enrichReviewedCandidate(candidate,extracted){
  if(!candidate||candidate.reviewedStatus!=="live"||!candidate.reviewedAt)
    throw new Error("Verify this specific job Live before recovering source details.");
  const job=candidate.job;
  if(!job||typeof job!=="object"||!candidate.apply||normalizeUrl(job.apply)!==normalizeUrl(candidate.apply))
    throw new Error("Official application URL differs from the reviewed record.");
  if(normalizeUrl(extracted?.sourceUrl)!==normalizeUrl(candidate.apply))
    throw new Error("The extracted page is not the exact reviewed official job URL.");
  if(employerKey(candidate.company)!==employerKey(extracted.company)||
     employerKey(job.company)!==employerKey(extracted.company))
    throw new Error("Employer identity differs from the reviewed job; no content was generated.");
  const originalRole=normalizeRole(job.role||candidate.role),scrapedRole=normalizeRole(extracted.role);
  if(!originalRole||!scrapedRole||!(scrapedRole===originalRole ||
      (originalRole.length>=10&&scrapedRole.startsWith(originalRole+" "))||
      (scrapedRole.length>=10&&originalRole.startsWith(scrapedRole+" "))))
    throw new Error("Job title differs from the reviewed requisition; verify it manually.");
  if(job.jobId&&extracted.jobId&&String(job.jobId).toLowerCase()!==String(extracted.jobId).toLowerCase())
    throw new Error("Job requisition IDs do not match.");
  const evidence=extracted.extraction||{};
  if(!evidence.structuredJobPosting&&!evidence.readerFallback&&!evidence.directFetch)
    throw new Error("The employer page did not provide readable source content.");
  const updated={...job};
  const recovered=[];
  if(!String(updated.elig||"").trim()&&evidence.eligibility&&String(extracted.elig||"").trim()){
    updated.elig=extracted.elig;recovered.push("eligibility");
  }
  if(!String(updated.desc||"").trim()&&evidence.description&&String(extracted.desc||"").trim()){
    updated.desc=extracted.desc;recovered.push("description");
  }
  if((!Array.isArray(updated.resp)||!updated.resp.some(x=>String(x||"").trim()))&&
      evidence.responsibilities&&Array.isArray(extracted.resp)&&extracted.resp.some(x=>String(x||"").trim())){
    updated.resp=extracted.resp.filter(x=>String(x||"").trim());recovered.push("responsibilities");
  }
  if(!String(updated.loc||"").trim()&&evidence.location&&extracted.loc&&extracted.loc!=="Not Specified"){
    updated.loc=extracted.loc;recovered.push("location");
  }
  if(!String(updated.sourceName||"").trim()&&recovered.length)
    updated.sourceName=extracted.sourceName;
  if(completeJob({...updated,status:"active"}))updated.status="active";
  const next={...candidate,job:updated};
  if(recovered.length){
    next.sourceEnrichment={fields:recovered,url:candidate.apply,source:extracted.extraction.source,
      evidenceVerifiedAt:new Date().toISOString()};
  }
  return {candidate:next,recovered,complete:completeJob(updated)};
}
