const ALIASES={
  "deloitte south asia":"deloitte","deloitte us india offices":"deloitte",
  "tata consultancy services tcs":"tata consultancy services",
  "tata consultancy services":"tata consultancy services",
  "jp morgan chase":"jpmorgan chase","jp morgan":"jpmorgan chase","jpmorgan":"jpmorgan chase",
  "hewlett packard enterprise hpe":"hpe","hewlett packard enterprise":"hpe",
  "lt technology services ltts":"l and t technology services",
  "l t technology services":"l and t technology services",
  "l and t technology services ltts":"l and t technology services",
  "tcs":"tata consultancy services","tata consultancy services limited":"tata consultancy services",
  "hcl":"hcltech","hcl technologies":"hcltech","hcl technologies limited":"hcltech",
  "ey":"ernst young","ernst and young":"ernst young","ernst & young":"ernst young",
  "ibm":"international business machines","ibm india":"international business machines",
  "pwc":"pricewaterhousecoopers","price waterhouse coopers":"pricewaterhousecoopers",
  "ntt data":"nttdata","ntt data services":"nttdata",
  "amazon india":"amazon","amazon development center":"amazon","amazon web services":"amazon","aws":"amazon",
  "google india":"google","google cloud":"google","alphabet":"google","microsoft india":"microsoft","microsoft azure":"microsoft",
  "deloitte usi":"deloitte","deloitte india":"deloitte",
  "cognizant technology solutions":"cognizant","capgemini engineering":"capgemini",
  "accenture solutions":"accenture","accenture india":"accenture"
};
export function employerKey(value){
  const text=String(value||"").normalize("NFKC").toLowerCase().replace(/&/g," and ").replace(/\b(?:pvt|private|ltd|limited|inc|llp|corp|corporation)\b/g," ").replace(/[^a-z0-9]+/g," ").trim().replace(/\s+/g," ");
  return ALIASES[text]||text;
}
export function allCandidates(batch){return [...(Array.isArray(batch?.priority)?batch.priority:[]),...(Array.isArray(batch?.backup)?batch.backup:[])];}
export function completeJob(j){
  if(!j||typeof j!=="object"||j.status!=="active")return false;
  if(!["company","role","loc","elig","desc","apply","sourceName"].every(k=>String(j[k]||"").trim()))return false;
  if(!Array.isArray(j.resp)||!j.resp.some(x=>String(x||"").trim()))return false;
  try{const u=new URL(j.apply);return u.protocol==="https:"&&Boolean(u.hostname)}catch{return false}
}
export function publishable(c){
  return Boolean(c&&c.reviewedStatus==="live"&&c.reviewedAt&&completeJob(c.job)
    &&String(c.apply||c.job.apply).trim()===String(c.job.apply).trim());
}
export function selectCandidates(batch,ids){
  if(!Array.isArray(ids)||ids.length<1||ids.length>10||new Set(ids).size!==ids.length||ids.some(x=>typeof x!=="string"||!x.trim())){
    throw Object.assign(new Error("Choose 1 to 10 different reviewed jobs."),{status:400});
  }
  const all=allCandidates(batch);
  const matches=ids.map(id=>all.find(c=>String(c.id)===id));
  if(matches.some(x=>!x))throw Object.assign(new Error("Selected job is no longer in this batch."),{status:409});
  if(matches.some(x=>!publishable(x)))throw Object.assign(new Error("Every selected job must be Live, complete and verified at its exact official URL."),{status:400});
  const employers=matches.map(x=>employerKey(x.company||x.job.company));
  if(employers.some(x=>!x)||new Set(employers).size!==employers.length){
    throw Object.assign(new Error("Select no more than one job per employer, including aliases."),{status:409});
  }
  return matches;
}
export function employerAudit(batch){
  const all=allCandidates(batch),seen=new Map(),duplicates=[];
  for(const c of all){
    const key=employerKey(c.company||c.job?.company);
    if(!key)duplicates.push({id:c.id,employer:"Missing employer"});
    else if(seen.has(key))duplicates.push({id:c.id,employer:c.company||c.job?.company,firstId:seen.get(key)});
    else seen.set(key,c.id);
  }
  return {total:all.length,unique:seen.size,duplicates,needsMore:Math.max(0,20-seen.size)};
}
export function categoryBucket(candidate){
  const j=candidate?.job||candidate||{};
  const cat=String(j.cat||candidate?.cat||"").toLowerCase();
  if(cat==="internship"||cat==="apprenticeship")return "intern";
  if(cat==="nonit"||cat==="walkin"||cat==="govt")return "nonit";
  const title=String(j.role||candidate?.role||"").toLowerCase();
  if(/\\b(internship|intern|apprentice|trainee)\\b/.test(title))return "intern";
  if(["it","campus","remote"].includes(cat))return "technical";
  return "unclassified";
}
export function batchCompositionAudit(batch){
  const targets={technical:6,intern:2,nonit:2};
  const report={};
  for(const [name,items] of [["priority",batch?.priority||[]],["backup",batch?.backup||[]]]){
    const counts={technical:0,intern:0,nonit:0,unclassified:0};
    for(const item of items)counts[categoryBucket(item)]++;
    report[name]={counts,targets,shortfalls:Object.fromEntries(Object.entries(targets).map(([k,n])=>[k,Math.max(0,n-counts[k])])),size:items.length};
  }
  return {...report,employers:employerAudit(batch)};
}
export function isFresherIT(c){
  const j=c.job||{},cat=String(j.cat||c.cat||"it").toLowerCase();
  const it=["it","campus","remote"].includes(cat);
  return it&&(j.expType==="fresher"||(/^(?:0\s*years?|fresher|early career)$/i).test(String(j.expYears||c.expYears||"").trim()));
}
export function reviewCounts(batch,chosen=[],published=[]){
  const all=allCandidates(batch),picked=new Set(chosen),pub=new Set(published);
  return {selected:picked.size,ready:all.filter(publishable).length,incomplete:all.filter(c=>c.reviewedStatus==="live"&&!publishable(c)).length,
    expired:all.filter(c=>c.reviewedStatus==="expired").length,alreadyPublished:all.filter(c=>pub.has(String(c.job?.apply||"").trim().toLowerCase())).length,
    fresherIT:all.filter(isFresherIT).length,...employerAudit(batch),composition:batchCompositionAudit(batch)};
}
