import {employerKey,isFresherIT} from "./review-rules.js";

export function evidenceScore(candidate){
 const reason=String(candidate.verificationReason||candidate.verification?.reason||"").toLowerCase();
 const j=candidate.job||{};
 let score=0;
 const uncertain=/blank (?:workday |client |oracle )?shell|rendered as a blank|client shell|http 406|captcha|access denied|blocked by/i.test(reason);
 const exact=/exact [^,.]*(?:page|listing|posting)/i.test(reason);
 const application=/apply (?:now|link|form)|application (?:control|form)|job-specific apply|active apply/i.test(reason);
 if(uncertain)score-=110;
 else if(exact&&application)score+=100;
 else if(exact)score+=40;
 else if(application)score+=30;
 if(/indexed (?:yesterday|last week|recently)|older (?:index|copy)/i.test(reason))score-=20;
 if(String(j.elig||"").trim())score+=15;
 if(String(j.desc||"").trim().length>=80)score+=10;
 if(Array.isArray(j.resp)&&j.resp.some(s=>String(s).trim()))score+=15;
 if(isFresherIT(candidate))score+=12;
 return score;
}
export function reprioritizeBeforeReview(batch){
 if(!batch||!Array.isArray(batch.priority)||!Array.isArray(batch.backup)||
     batch.priority.length!==10||batch.backup.length!==10)return {changed:false,reason:"Batch must contain 10 Priority and 10 Backup jobs.",batch};
 const all=[...batch.priority,...batch.backup];
 if(all.some(j=>j.reviewedAt||!["","unreviewed"].includes(String(j.reviewedStatus||""))))
   return {changed:false,reason:"Manual review decisions already exist; do not reorder.",batch};
 const employers=all.map(j=>employerKey(j.company||j.job?.company));
 if(employers.some(k=>!k)||new Set(employers).size!==20||new Set(all.map(j=>String(j.id))).size!==20)
   return {changed:false,reason:"20 unique jobs from 20 employers are required.",batch};
 const ranked=all.map((j,index)=>({j,index,score:evidenceScore(j)}))
   .sort((a,b)=>b.score-a.score||a.index-b.index);
 const ordered=ranked.map(x=>x.j);
 const changed=ordered.some((j,i)=>j.id!==all[i].id);
 if(!changed)return {changed:false,reason:"Already ranked by source evidence.",batch};
 return {changed:true,reason:"Ranked by exact-page evidence; ambiguous shells remain unconfirmed, not expired.",
   batch:{...batch,priority:ordered.slice(0,10),backup:ordered.slice(10),
     ranking:{method:"official-evidence-v1",rankedAt:new Date().toISOString(),
       warning:"Uncertain shells are not proof of expiry. Manually verify exact URLs before publishing."}}};
}
