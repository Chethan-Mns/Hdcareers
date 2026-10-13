/** Bind exact owner decisions from the server-side review batch, never from the caller's job payload. */
export function attachReviewedProof(jobs,batch,ids){
  if(!Array.isArray(jobs)||!Array.isArray(ids)||jobs.length!==ids.length||!batch||batch.status!=="reviewing")throw new Error("Approved job selection has changed.");
  const candidates=[...(batch.priority||[]),...(batch.backup||[])];
  return jobs.map((job,i)=>{
    const candidate=candidates.find(c=>String(c.id)===String(ids[i]));
    if(!candidate||candidate.reviewedStatus!=="live"||!candidate.reviewedAt||candidate.job?.status!=="active")throw new Error("Exact human Live review is missing for "+ids[i]);
    if(candidate.apply!==candidate.job?.apply||candidate.apply!==job.apply||candidate.job.manualLiveVerifiedAt!==candidate.reviewedAt)throw new Error("Reviewed official URL or original verification timestamp changed for "+ids[i]);
    return {...job,manualLiveVerifiedAt:candidate.reviewedAt,manualLiveVerifiedUrl:candidate.apply};
  });
}
