import {employerKey,isFresherIT} from "./review-rules.js";

// Large global employers preferred for the HD Careers fresher audience.
// Prefer source-verifiable jobs: brand priority never overrides weak Live evidence.
const TOP_EMPLOYERS=[
 "Deloitte","Deloitte USI","Deloitte South Asia","KPMG","EY","PwC",
 "Accenture","Capgemini","HCLTech","Cognizant","Tech Mahindra","TCS",
 "Wipro","Dell","Dell Technologies","HP","HP Inc.","HPE",
 "Hewlett Packard Enterprise","Landmark Group","CGI","Flipkart","Amazon",
 "JPMorgan Chase","JP Morgan","JPMorgan","Google","Microsoft","IBM",
 "Infosys","Visa","Cisco","Qualcomm","GE HealthCare","Bosch","Target",
 "NTT DATA","Oracle","SAP","Salesforce","American Express","Intel",
 "Walmart","LTTS","L&T Technology Services","NetApp","State Street",
 "Lam Research","Adobe","Rubrik","MongoDB","ServiceNow","Virtusa"
];
const HIGH_PRIORITY=new Set(TOP_EMPLOYERS.map(employerKey));
const SECOND_TIER=new Set(["Thermo Fisher Scientific","Cargill","AHEAD","Marmon","Persistent Systems",
 "Hexaware","EPAM Systems","Genpact","Kyndryl","Zensar Technologies","Brillio"].map(employerKey));

function category(candidate){
 const j=candidate.job||{};
 const cat=String(j.cat||candidate.cat||"").toLowerCase();
 const role=String(j.role||candidate.role||"");
 if(["internship","apprenticeship"].includes(cat)||/\b(?:intern|internship|apprentice|apprenticeship)\b/i.test(role))return "training";
 if(["nonit","non-it","non it"].includes(cat))return "nonit";
 if(isFresherIT(candidate)&&!/\b(?:senior|lead|manager|director|principal|architect|staff|head)\b/i.test(role))return "fresherIT";
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

export function reprioritizeBeforeReview(batch,{publishedJobs=[],deliveries=[],ownerVerdicts=[],watchlist=null,now=new Date()}={}){
 if(!batch||!Array.isArray(batch.priority)||!Array.isArray(batch.backup)||
     batch.priority.length<1||batch.priority.length>10||batch.backup.length<1||batch.backup.length>10||
     batch.priority.length+batch.backup.length<15)
   return {changed:false,reason:"Rank only valid shortlists with 1-10 Priority, 1-10 Backup and at least 15 distinct candidates.",batch};
 const all=[...batch.priority,...batch.backup];
 if(all.some(j=>j.reviewedAt||!["","unreviewed"].includes(String(j.reviewedStatus||""))))
   return {changed:false,reason:"Manual review decisions already exist; do not reorder.",batch};
 const employers=all.map(j=>employerKey(j.company||j.job?.company));
 if(employers.some(k=>!k)||new Set(employers).size!==all.length||new Set(all.map(j=>String(j.id))).size!==all.length)
   return {changed:false,reason:"20 unique jobs from 20 employers are required.",batch};
 const ledger=Array.isArray(deliveries)?deliveries:Object.values(deliveries||{});
 const sent=ledger.filter(x=>x&&x.status==="delivered");
 const byPage=new Map(publishedJobs.map(j=>[String(j.page||""),j]));
 const history=sent.map(d=>({company:byPage.get(d.page)?.company,deliveredAt:d.deliveredAt}))
   .filter(d=>d.company&&d.deliveredAt);
 const seenPublished=all.filter(j=>alreadyPublished(j,publishedJobs));
 const ownerClosedUrls=new Set((Array.isArray(ownerVerdicts)?ownerVerdicts:[])
  .filter(v=>v.manualVerdict==="expired").map(v=>exactUrl(v.officialUrl)).filter(Boolean));
 const ownerClosed=all.filter(j=>ownerClosedUrls.has(exactUrl(j.job?.apply||j.apply)));
 const fresh=all.filter(j=>!alreadyPublished(j,publishedJobs)&&!ownerClosedUrls.has(exactUrl(j.job?.apply||j.apply)));
 if(!fresh.length)return {changed:false,reason:"No new candidates remain after published and owner-confirmed expired exclusions; discover fresh official requisitions.",batch};
 const watched=new Set(Object.values(watchlist?.categories||{}).flat().map(employerKey));
 const matchedWatchlist=watched.size>0;
 const deloitte=new Set(["Deloitte","Deloitte USI","Deloitte South Asia"].map(employerKey));
 const big4AndMnc=new Set(["KPMG","EY","PwC","Accenture","Cognizant","Capgemini"].map(employerKey));
 const majorIT=new Set(["Infosys","TCS","Tata Consultancy Services (TCS)","Tech Mahindra","Wipro","HCLTech"].map(employerKey));
 const desiredBrand=(company)=>{
  if(!matchedWatchlist)return HIGH_PRIORITY.has(company)?80:SECOND_TIER.has(company)?25:0;
  if(deloitte.has(company))return 400;
  if(big4AndMnc.has(company))return 230;
  if(majorIT.has(company))return 180;
  if(watched.has(company))return 110;
  return -250; // outside the owner's 87 companies only when no qualifying watchlist jobs fill quota
 };
 const ranked=fresh.map((j,index)=>{
  const company=employerKey(j.company||j.job?.company);
  return {j,index,score:evidenceScore(j)+desiredBrand(company)+recentlyPostedScore(j,history,now)};
 }).sort((a,b)=>b.score-a.score||a.index-b.index);
 const picked=[],chosen=new Set();
 const take=(track,n)=>{
  for(const c of ranked){
   if(picked.length>=10||n<=0)break;
   // An unconfirmed role belongs in backups/review, never in an auto-live shortlist.
   if(c.j.verificationVerdict!=="live"||chosen.has(c.j.id)||category(c.j)!==track)continue;
   picked.push(c.j);chosen.add(c.j.id);n--;
  }
 };
 take("fresherIT",8);take("nonit",1);take("training",1);
 if(!picked.length)return {changed:false,reason:"No fresh Live-evidenced candidate fits the 8/1/1 mix; do not publish or relabel jobs.",batch};
 const selected={
  fresherIT:picked.filter(j=>category(j)==="fresherIT").length,
  nonIT:picked.filter(j=>category(j)==="nonit").length,
  training:picked.filter(j=>category(j)==="training").length
 };
 const shortfalls={fresherIT:Math.max(0,8-selected.fresherIT),nonIT:Math.max(0,1-selected.nonIT),training:Math.max(0,1-selected.training)};
 // Put shortfall-category candidates needing independent verification into backups
 // ahead of irrelevant experienced roles, but NEVER into the Live shortlist.
 const needed=c=>((category(c.j)==="fresherIT"&&shortfalls.fresherIT>0)||
    (category(c.j)==="nonit"&&shortfalls.nonIT>0)||
    (category(c.j)==="training"&&shortfalls.training>0))?1:0;
 // Unconfirmed ATS shells/redirects must NOT reach the owner as supposed live backup jobs.
 // Keep an exact-source recheck record so they aren't silently lost.
 const heldForRecheck=ranked.filter(c=>!chosen.has(c.j.id)&&c.j.verificationVerdict!=="live")
   .map(c=>({id:c.j.id,company:c.j.company||c.j.job?.company,
     role:c.j.role||c.j.job?.role,officialUrl:c.j.job?.apply||c.j.apply,
     verificationVerdict:c.j.verificationVerdict||"unconfirmed",
     verificationReason:c.j.verificationReason||"Official availability unconfirmed"}));
 const backupCandidates=ranked.filter(c=>!chosen.has(c.j.id)&&c.j.verificationVerdict==="live")
   .sort((a,b)=>needed(b)-needed(a)||b.score-a.score||a.index-b.index);
 const backups=backupCandidates.slice(0,10).map(c=>c.j);
 const deferred=backupCandidates.slice(10).map(c=>({id:c.j.id,company:c.j.company||c.j.job?.company}));
 const ordered=[...picked,...backups];
 const changed=ordered.length!==all.length||ordered.some((j,i)=>j.id!==all[i]?.id);
 const goalMet=Object.values(shortfalls).every(v=>v===0);
 const reason=`Selected ${picked.length} candidates: ${selected.fresherIT} fresher IT, ${selected.nonIT} non-IT, ${selected.training} internship/apprenticeship; ${seenPublished.length} already-published and ${ownerClosed.length} owner-confirmed expired jobs excluded. ${goalMet?"8/1/1 quota filled.":"Missing categories must be discovered; do not relabel experienced roles."}`;
 if(!changed)return {changed:false,reason,batch};
 return {changed:true,reason,
  batch:{...batch,priority:picked,backup:backups,
   ranking:{method:"official-evidence-quota-diversity-v2",rankedAt:now.toISOString(),
     target:{fresherIT:8,nonIT:1,training:1},selected,shortfalls,
     excludedPreviouslyPublished:seenPublished.map(x=>({id:x.id,company:x.company||x.job?.company})),
     excludedOwnerExpired:ownerClosed.map(x=>({id:x.id,company:x.company||x.job?.company})),
     deferredForFreshDiscovery:deferred,
     needsSourceVerification:heldForRecheck,
     warning:"Only confirmed Live-evidenced jobs reach Priority/Backup. Unconfirmed exact URLs are saved for separate source rechecking, never silently marked Expired."}}};
}
