import {employerKey,isFresherIT} from "./review-rules.js";

// Keep job identity while dropping only marketing/tracking parameters.
const TRACK=/^(utm_.+|gh_src|source|src|ref|referrer|feedid|trackingid|trk|campaign|fbclid|gclid)$/i;
export function jobUrl(value){
  try{
    const u=new URL(String(value||"").trim());
    if(u.protocol!=="https:")return "";
    const query=[...u.searchParams.entries()].filter(([key])=>!TRACK.test(key))
      .sort(([ak,av],[bk,bv])=>ak.localeCompare(bk)||av.localeCompare(bv));
    const q=new URLSearchParams(query).toString();
    return u.hostname.toLowerCase()+u.pathname.replace(/\/$/,"").toLowerCase()+(q?"?"+q:"");
  }catch{return ""}
}
function jobOf(c){return c?.job&&typeof c.job==="object"?c.job:c||{}}
function keys(candidate){
  const j=jobOf(candidate),employer=employerKey(j.company||candidate.company);
  const url=jobUrl(j.apply||candidate.apply);
  const req=String(j.jobId||candidate.jobId||"").trim().toLowerCase();
  const role=String(j.role||candidate.role||"").trim().toLowerCase().replace(/\s+/g," ");
  const page=String(j.page||candidate.page||"").trim().replace(/^\//,"").toLowerCase();
  return {employer,url,req:employer&&req?employer+"|"+req:"",role:employer&&role?employer+"|"+role:"",page};
}
function category(candidate){
  const j=jobOf(candidate),cat=String(j.cat||candidate.cat||"").toLowerCase(),role=String(j.role||candidate.role||"");
  if(["internship","apprenticeship"].includes(cat)||/\b(intern|internship|apprentice|apprenticeship)\b/i.test(role))return "training";
  if(cat==="nonit")return "nonIT";
  if(isFresherIT(candidate)&&!/\b(senior|lead|manager|director|principal|architect|staff|head)\b/i.test(role))return "fresherIT";
  return "unclassified";
}
function targets(rows){
  const counts={fresherIT:0,nonIT:0,training:0,unclassified:0};
  for(const candidate of rows)counts[category(candidate)]++;
  return {size:rows.length,counts,shortfalls:{
    fresherIT:Math.max(0,6-counts.fresherIT),
    nonIT:Math.max(0,2-counts.nonIT),
    training:Math.max(0,2-counts.training)
  }};
}
function match(k,prior){
  if(k.url&&prior.url&&k.url===prior.url)return "same_official_job_url";
  if(k.req&&prior.req&&k.req===prior.req)return "same_employer_requisition";
  if(k.page&&prior.page&&k.page===prior.page)return "same_published_page";
  return "";
}
export function filterDiscoveryDuplicates(batch,{publishedJobs=[],deliveries={},archivedBatches=[],ownerVerdicts=[]}={}){
  if(batch?.status!=="reviewing"||!Array.isArray(batch.priority)||!Array.isArray(batch.backup)){
    return {changed:false,batch,reason:"Not a new reviewing batch"};
  }
  const all=[...batch.priority,...batch.backup];
  if(all.some(c=>c.reviewedAt||!["","unreviewed"].includes(String(c.reviewedStatus||"")))){
    return {changed:false,batch,reason:"Owner review already exists; do not change decisions"};
  }
  const published=(Array.isArray(publishedJobs)?publishedJobs:[]).map(keys);
  const historical=(Array.isArray(archivedBatches)?archivedBatches:[])
    .flatMap(b=>[...(b?.priority||[]),...(b?.backup||[])])
    .map(keys);
  const expired=(Array.isArray(ownerVerdicts)?ownerVerdicts:[])
    .filter(v=>String(v.manualVerdict||"").toLowerCase()==="expired")
    .map(v=>keys({company:v.company,apply:v.officialUrl,jobId:v.jobId,role:v.role}));
  const receipts=Object.values(deliveries||{})
    .filter(x=>x?.status==="delivered").map(x=>String(x.page||"").trim().toLowerCase());
  const sentPages=new Set(receipts);
  const seen=[],employers=new Set(),removed=[];
  const keep=group=>group.filter(c=>{
    const k=keys(c),id=String(c.id||""),company=c.company||c.job?.company||"";
    let reason="";
    if(!k.url)reason="invalid_or_missing_official_https_url";
    else if(published.some(p=>match(k,p)||k.employer===p.employer&&k.role&&p.role===k.role))reason="already_published";
    else if(k.page&&sentPages.has(k.page))reason="already_sent_to_telegram";
    else if(expired.some(p=>match(k,p)))reason="owner_confirmed_expired";
    else if(historical.some(p=>match(k,p)))reason="previously_reviewed_official_requisition";
    else if(seen.some(p=>match(k,p)||k.employer===p.employer&&k.role&&p.role===k.role))reason="duplicate_within_new_shortlist";
    else if(employers.has(k.employer))reason="repeated_employer_across_priority_and_backup";
    if(reason){removed.push({id,company,reason,officialUrl:c.job?.apply||c.apply||""});return false}
    seen.push(k);employers.add(k.employer);return true;
  });
  const priority=keep(batch.priority),backup=keep(batch.backup);
  const tally={priority:targets(priority),backup:targets(backup)};
  const previous=batch.discoveryAudit;
  const accumulated=[...(previous?.duplicateExclusions||[]),...removed];
  const discoveryAudit={...tally,target:{priority:10,backup:10},remaining:priority.length+backup.length,
    duplicateExclusions:accumulated,
    excludedCount:accumulated.length,
    needsFreshDiscovery:priority.length!==10||backup.length!==10||
      Object.values(tally).some(t=>Object.values(t.shortfalls).some(n=>n>0)),
    note:"Incomplete shortlists are reported, never padded with duplicate or unverified jobs."};
  const changed=removed.length>0||!previous||
    JSON.stringify({...previous,duplicateExclusions:undefined})!==JSON.stringify({...discoveryAudit,duplicateExclusions:undefined});
  const discoverySummary=batch.discoverySummary&&typeof batch.discoverySummary==="object"
    ?{...batch.discoverySummary,duplicatesExcluded:Math.max(Number(batch.discoverySummary.duplicatesExcluded)||0,accumulated.length),
      distinctEmployers:employers.size,
      liveSelected:[...priority,...backup].filter(c=>c.verificationVerdict==="live").length,
      shortfall:discoveryAudit.needsFreshDiscovery
        ?(priority.length+"/10 Priority and "+backup.length+"/10 Backup; fresh verified category-matched employers needed")
        :"No shortlist shortfall."}
    :undefined;
  return {changed,batch:changed?{...batch,priority,backup,discoveryAudit,
      ...(discoverySummary?{discoverySummary}:{})}:batch,removed,
    reason:removed.length+" duplicate or previously published candidates excluded; "+(priority.length+backup.length)+"/20 unique candidates remain."};
}
