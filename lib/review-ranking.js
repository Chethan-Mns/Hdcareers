import {employerKey,isFresherIT} from "./review-rules.js";

// Owner-priority employers. Aliases are normalized through employerKey.
const TOP_EMPLOYERS=[
 "Google","Microsoft","Amazon","JPMorgan Chase","Visa","Cisco","Qualcomm",
 "Accenture","Infosys","TCS","Wipro","HCLTech","IBM","PwC","KPMG","EY",
 "Deloitte","Deloitte South Asia","Bosch","Tech Mahindra","L&T Technology Services",
 "NetApp","State Street","Lam Research","Target","Rubrik","MongoDB",
 "GE HealthCare","Walmart","Capgemini","Cognizant","NTT DATA","Virtusa",
 "Thermo Fisher Scientific","Cargill","Flipkart","American Express","SAP",
 "Salesforce","Intel","Oracle","Adobe","ServiceNow","HPE","Larsen & Toubro",
 "AHEAD","Marmon","Hyreo","SingleStore","SuperApp","New Street Technologies"
];
const STRONG=new Set(TOP_EMPLOYERS.slice(0,21).map(employerKey));
const PREFERRED=new Set(TOP_EMPLOYERS.map(employerKey));

function category(candidate){
 const j=candidate.job||{};
 const cat=String(j.cat||candidate.cat||"").toLowerCase();
 const role=String(j.role||candidate.role||"");
 if(["internship","apprenticeship"].includes(cat)||/\b(?:intern|internship|apprentice|apprenticeship)\b/i.test(role))return "training";
 if(["nonit","non-it","non it"].includes(cat))return "nonit";
 if(isFresherIT(candidate))return "fresherIT";
 return "other";
}

function exactUrl(value){
 try {
  const url=new URL(String(value||""));
  return url.protocol==="https:"?url.hostname.toLowerCase()+url.pathname.replace(/\/$/,"")+url.search:"";
 }catch{return "";}
}
function alreadyPublished(candidate,existing){
 const j=candidate.job||{},name=employerKey(j.company||candidate.company),role=String(j.role||candidate.role||"").trim().toLowerCase(),req=String(j.jobId||candidate.jobId||"").trim().toLowerCase(),url=exactUrl(j.apply||candidate.apply);
 return existing.some(p=>{
  if(url&&exactUrl(p.apply)===url)return true;
  if(employerKey(p.company)!==name)return false;
  const oldReq=String(p.jobId||"").trim().toLowerCase();
  if(req&&oldReq&&req===oldReq)return true;
  return role&&String(p.role||"").trim().toLowerCase()===role;
 });
}

function recentlyPostedScore(candidate,history,now){
 const name=employerKey(candidate.company||candidate.job?.company);
 let recent=Infinity;
 for(const entry of history){
  if(employerKey(entry.company)!==name)continue;
  const t=Date.parse(entry.deliveredAt||"");
  if(!Number.isFinite(t))continue;
  const days=(now.getTime()-t)/86400000;
  if(days>=0&&days<recent)recent=days;
 }
 if(recent<7)return -180;
 if(recent<14)return -120;
 if(recent<30)return -50;
 return 0;
}

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
 if(candidate.verificationVerdict==="unconfirmed"||candidate.verificationVerdict==="review")score-=120;
 if(candidate.verificationVerdict==="expired")score-=10000;
 return score;
}

export function reprioritizeBeforeReview(batch,{publishedJobs=[],deliveries=[],now=new Date()}={}){
 if(!batch||!Array.isArray(batch.priority)||!Array.isArray(batch.backup)||
     batch.priority.length!==10||batch.backup.length!==10)return {changed:false,reason:"Batch must contain 10 Priority and 10 Backup jobs.",batch};
 const all=[...batch.priority,...batch.backup];
 if(all.some(j=>j.reviewedAt||!["","unreviewed"].includes(String(j.reviewedStatus||""))))
   return {changed:false,reason:"Manual review decisions already exist; do not reorder.",batch};
 const employers=all.map(j=>employerKey(j.company||j.job?.company));
 if(employers.some(k=>!k)||new Set(employers).size!==20||new Set(all.map(j=>String(j.id))).size!==20)
   return {changed:false,reason:"20 unique jobs from 20 employers are required.",batch};
 const ledger=Array.isArray(deliveries)?deliveries:Object.values(deliveries||{});
 const sent=ledger.filter(x=>x&&x.status==="delivered");
 const byPage=new Map(publishedJobs.map(j=>[String(j.page||""),j]));
 const history=sent.map(d=>({company:byPage.get(d.page)?.company,deliveredAt:d.deliveredAt}))
   .filter(d=>d.company&&d.deliveredAt);
 const seenPublished=all.filter(j=>alreadyPublished(j,publishedJobs));
 const fresh=all.filter(j=>!alreadyPublished(j,publishedJobs));
 if(!fresh.length)return {changed:false,reason:"All 20 candidates were already published. Discover fresh official requisitions.",batch};
 const ranked=fresh.map((j,index)=>{
  const company=employerKey(j.company||j.job?.company);
  const employerBonus=STRONG.has(company)?65:PREFERRED.has(company)?35:0;
  return {j,index,score:evidenceScore(j)+employerBonus+recentlyPostedScore(j,history,now)};
 }).sort((a,b)=>b.score-a.score||a.index-b.index);
 const picked=[],chosen=new Set();
 const take=(track,n)=>{
  for(const c of ranked){
   if(picked.length>=10||n<=0)break;
   if(chosen.has(c.j.id)||category(c.j)!==track)continue;
   picked.push(c.j);chosen.add(c.j.id);n--;
  }
 };
 take("fresherIT",8);take("nonit",1);take("training",1);
 for(const c of ranked){
  if(picked.length>=10)break;
  if(!chosen.has(c.j.id)){picked.push(c.j);chosen.add(c.j.id);}
 }
 const backups=ranked.filter(c=>!chosen.has(c.j.id)).slice(0,10).map(c=>c.j);
 const selected={
  fresherIT:picked.filter(j=>category(j)==="fresherIT").length,
  nonIT:picked.filter(j=>category(j)==="nonit").length,
  training:picked.filter(j=>category(j)==="training").length
 };
 const shortfalls={fresherIT:Math.max(0,8-selected.fresherIT),nonIT:Math.max(0,1-selected.nonIT),training:Math.max(0,1-selected.training)};
 const ordered=[...picked,...backups];
 const changed=ordered.length!==all.length||ordered.some((j,i)=>j.id!==all[i]?.id);
 const goalMet=Object.values(shortfalls).every(v=>v===0);
 const reason=`Selected ${picked.length} candidates: ${selected.fresherIT} fresher IT, ${selected.nonIT} non-IT, ${selected.training} internship/apprenticeship; ${seenPublished.length} already-published jobs excluded. ${goalMet?"8/1/1 quota filled.":"Missing categories must be discovered; do not relabel experienced roles."}`;
 if(!changed)return {changed:false,reason,batch};
 return {changed:true,reason,
  batch:{...batch,priority:picked,backup:backups,
   ranking:{method:"official-evidence-quota-diversity-v2",rankedAt:now.toISOString(),
     target:{fresherIT:8,nonIT:1,training:1},selected,shortfalls,
     excludedPreviouslyPublished:seenPublished.map(x=>({id:x.id,company:x.company||x.job?.company})),
     warning:"Ranked candidates are not verified for publication. Recheck the exact job and application before posting; unconfirmed jobs remain held."}}};
}
