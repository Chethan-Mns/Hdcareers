import {completeJob} from "./review-rules.js";

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
  // Keep the employer/title supplied by the curated requisition.
  // Minor metadata naming differences from the extraction do not block detail recovery.
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
