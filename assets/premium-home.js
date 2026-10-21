/* Premium homepage enhancements, consuming the existing verified JOBS array. */
(function(){
"use strict";
function el(id){return document.getElementById(id)}
function escapeHTML(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function parseDate(j){for(const raw of [j.verifiedDate,j.date]){const d=Date.parse(raw||"");if(Number.isFinite(d))return d}return 0}
function goToResults(){const s=el("resultsSection");if(s)s.scrollIntoView({behavior:window.matchMedia("(prefers-reduced-motion: reduce)").matches?"auto":"smooth",block:"start"})}
function pickCompany(name){const input=el("companyFilter");if(!input)return;resetFilters();input.value=name;filterAndScrollNow();goToResults()}
function exploreAll(){if(typeof resetFilters==="function")resetFilters();const u=new URL(location.href);if(u.searchParams.has("company")){u.searchParams.delete("company");history.replaceState(null,"",u.pathname+u.search+u.hash)}goToResults()}
function iconLogo(j,size){return typeof companyLogo==="function"?companyLogo(j,size||"w-14 h-14"):"<span>★</span>"}
function render(){
  if(typeof JOBS==="undefined")return;
  const active=JOBS.filter(x=>x.status!=="expired");
  const unique=new Set(active.map(j=>j.company).filter(Boolean));
  const count=el("hdpJobs"),employers=el("hdpEmployers");
  if(count)count.textContent=active.length;if(employers)employers.textContent=unique.size;
  const mini=el("hdpArtJobs");
  if(mini){mini.innerHTML=active.slice().sort((a,b)=>parseDate(b)-parseDate(a)).slice(0,3).map((j,i)=>'<div class="hdp-art-job" style="--i:'+i+'"><span class="hdp-art-mini-logo">'+iconLogo(j,"w-8 h-8")+'</span><span class="hdp-art-mini-copy"><b>'+escapeHTML(j.company)+'</b><small>'+escapeHTML(j.role)+'</small></span><span class="hdp-art-mini-arrow">↗</span></div>').join('')}
  // Data-driven featured employers: every Active employer can qualify. Recognizable
  // brands are favored only on a TIE, never hard-pinned over a higher Active count.
  const recognized=new Set(["Deloitte","Deloitte South Asia","EY","PwC","KPMG","Google","Microsoft","Amazon","Accenture","HCLTech","Cognizant","TCS","Infosys","Wipro","IBM","Visa","Rubrik","Capgemini","Bosch","Cisco","Salesforce","MongoDB","Oracle","Adobe","JPMorganChase","JPMorgan Chase","GE HealthCare","Qualcomm","Walmart","Apple","Flipkart","Intel","Samsung","State Street"]);
  const byEmployer=new Map();
  for(const job of active){
    const name=String(job.company||"").trim();
    if(!name)continue;
    const record=byEmployer.get(name);
    if(record){record.jobs.push(job);record.lastVerified=Math.max(record.lastVerified,parseDate(job))}
    else byEmployer.set(name,{name,jobs:[job],lastVerified:parseDate(job)});
  }
  const candidates=[...byEmployer.values()].sort((a,b)=>
    b.jobs.length-a.jobs.length ||
    Number(recognized.has(b.name))-Number(recognized.has(a.name)) ||
    b.lastVerified-a.lastVerified ||
    a.name.localeCompare(b.name)
  ).slice(0,6);
  const comps=el("hdpCompanies");
  if(comps){comps.innerHTML=candidates.map(c=>{
    return '<button type="button" class="hdp-company" data-hdp-company="'+escapeHTML(c.name)+'">'+iconLogo(c.jobs[0])+'<h3>'+escapeHTML(c.name)+'</h3><span class="hdp-count">'+c.jobs.length+' active '+(c.jobs.length===1?"listing":"listings")+' →</span></button>'
  }).join("");comps.querySelectorAll("[data-hdp-company]").forEach(button=>button.addEventListener("click",()=>pickCompany(button.dataset.hdpCompany)))}
  const recent=el("hdpRecent");
  if(recent){
    const records=active.slice().sort((a,b)=>parseDate(b)-parseDate(a)).slice(0,4);
    recent.innerHTML=records.map(j=>'<article class="hdp-featured-item"><div class="hdp-job-company">'+iconLogo(j,"w-10 h-10")+'<span>'+escapeHTML(j.company)+'</span></div><h3>'+escapeHTML(j.role)+'</h3><p><i class="fa-solid fa-location-dot"></i> '+escapeHTML(j.loc||"Check official listing")+'</p><div class="flex flex-wrap gap-1.5"><span class="hdp-tag">'+escapeHTML(j.cat||"Job")+'</span><span class="hdp-tag">'+escapeHTML(j.expType==="not-specified"?"Eligibility on official listing":j.expType||"See eligibility")+'</span></div><a class="hdp-apply" href="'+escapeHTML(j.page)+'">View &amp; Apply →</a></article>').join("")
  }
  const all=el("hdpAllJobs");if(all)all.addEventListener("click",exploreAll);
  const view=el("hdpViewJobs");if(view)view.addEventListener("click",exploreAll);
}
function init(){render();const query=new URLSearchParams(window.location.search);const company=query.get("company"),city=query.get("location");if((company||city)&&typeof resetFilters==="function"){resetFilters();if(company&&el("companyFilter"))el("companyFilter").value=company;if(city&&el("locationFilter"))el("locationFilter").value=city;if(typeof renderJobs==="function")renderJobs();goToResults()}}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);else init();
})();