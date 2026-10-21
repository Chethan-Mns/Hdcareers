(()=>{"use strict";
const $=s=>document.getElementById(s);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const reduced=window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const colors=["#4285F4","#34A853","#FBBC05","#EA4335","#8162CA","#8191A9"];
const prefix=document.body.dataset.prefix||"";
function countTo(element,number){if(!element||!Number.isFinite(number))return;const n=Math.round(number);if(reduced){element.textContent=String(n);return}let start;function tick(t){start??=t;const p=Math.min(1,(t-start)/800);element.textContent=String(Math.round(n*(1-(1-p)**3)));if(p<1)requestAnimationFrame(tick)}requestAnimationFrame(tick)}
function showCards(){const cards=[...document.querySelectorAll(".hi-shown")];if(reduced||!("IntersectionObserver" in window)){cards.forEach(c=>c.classList.add("active"));return}const observer=new IntersectionObserver(entries=>{for(const entry of entries){if(entry.isIntersecting){entry.target.classList.add("active");observer.unobserve(entry.target)}}},{threshold:.09});cards.forEach(c=>observer.observe(c))}
function ringGradient(segs,palette=colors){const all=segs.reduce((v,x)=>v+x.count,0)||1;let begin=0;const stops=segs.map((x,i)=>{const end=begin+x.count/all*100,one=palette[i%palette.length]+" "+begin.toFixed(3)+"% "+end.toFixed(3)+"%";begin=end;return one});return "conic-gradient("+stops.join(",")+")"}
function showExperience(d){const n=d.active||0,sections=[{label:"Fresher",count:d.freshers||0},{label:"Experienced",count:d.experienced||0}],other=Math.max(0,n-sections[0].count-sections[1].count);sections.push({label:"Unspecified",count:other});
const ring=$("hiRoleRing");if(ring)ring.style.background=ringGradient(sections,colors.slice(0,3));
countTo($("hiRingTotal"),n);
$("hiRoleLegend").innerHTML=sections.map((section,i)=>'<div class="hi-leg"><span class="hi-legend-dot" style="background:'+colors[i]+'"></span><span>'+section.label+'</span><b>'+section.count+'</b></div>').join("")}
function showEmployers(d){const root=$("hiCompanies"),entries=(d.topCompanies||[]).slice(0,8);if(!entries.length){root.innerHTML='<p class="hi-empty">Employer information unavailable.</p>';return}
root.innerHTML=entries.map((item,i)=>{const path=typeof item.logo==="string"&&/^assets\/[a-z0-9/_-]+\.(?:png|jpg|jpeg|webp|svg|ico)$/i.test(item.logo)?prefix+item.logo:"";
const image=path?'<img loading="lazy" src="'+esc(path)+'" alt="'+esc(item.name)+' logo" onerror="this.hidden=true;this.nextElementSibling.hidden=false"><span class="hi-logo-fallback" hidden>'+esc(item.name.slice(0,1))+'</span>':'<span class="hi-logo-fallback">'+esc(item.name.slice(0,1))+'</span>';
return '<button type="button" class="hi-employer" style="--order:'+i+'" data-company="'+esc(item.name)+'" aria-label="View '+esc(item.name)+' jobs"><span class="hi-employer-logo">'+image+'</span><span class="hi-employer-copy"><strong>'+esc(item.name)+'</strong><small>'+item.count+' '+(item.count===1?'Active job':'Active jobs')+'</small></span><span class="hi-employer-arrow">↗</span></button>'}).join("");
root.querySelectorAll("[data-company]").forEach(b=>b.addEventListener("click",()=>location.assign(prefix+"index.html?company="+encodeURIComponent(b.dataset.company))))}
function skillMark(name){
 const k=String(name||"").toLowerCase().replace(/[^a-z+]/g,"");
 const files={"python":"python","java":"java","javascript":"javascript","c++":"cplusplus","linux":"linux"};
 const img=files[k];
 if(img)return '<img class="hi-skill-logo" src="'+prefix+'assets/skill-logos/'+img+'.svg" loading="lazy" alt="'+esc(name)+' logo">';
 const paths={
  "sql":'<ellipse cx="24" cy="11" rx="15" ry="6"/><path d="M9 11v25c0 9 30 9 30 0V11M9 23c0 8 30 8 30 0"/>',
  "restapis":'<circle cx="24" cy="24" r="15"/><path d="M9 24h30M24 9c-8 8-8 22 0 30M24 9c8 8 8 22 0 30"/>',
  "algorithms":'<path d="m12 12 12-7 12 7v11l-12 7-12-7zM24 30v10M16 40h16M12 23l-7 6 7 6M36 23l7 6-7 6"/>',
  "networking":'<circle cx="24" cy="9" r="5"/><circle cx="9" cy="37" r="5"/><circle cx="39" cy="37" r="5"/><path d="M21 14 12 32M27 14l9 18M14 37h20"/>',
  "problemsolving":'<path d="M18 12a9 9 0 0 1 16 6c0 7-10 8-10 15M20 41h8M24 5v4M11 10l3 3M37 10l-3 3"/>',
  "communication":'<path d="M9 11h30v22H22l-10 7v-7H9zM16 19h16M16 25h12"/>',
 };
 const shape=paths[k]||'<path d="M10 15h28v19H22l-7 7v-7h-5zM16 23h16"/>';
 return '<svg class="hi-skill-logo hi-skill-generic" viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+shape+'</svg>'
}
function showSkills(d){
 const root=$("hiSkills"),items=(d.topSkills||[]).slice(0,12);
 if(!items.length){root.innerHTML='<p class="hi-empty">Skill data is not available.</p>';return}
 const max=Math.max(1,...items.map(x=>x.count));
 root.innerHTML=items.map((p,i)=>{
   const size=Math.max(116,Math.min(155,116+39*p.count/max));
   return '<div class="hi-skill" style="--size:'+Math.round(size)+'px;--step:'+i+';--drift:'+(4+i%4)+'s" title="'+esc(p.label)+' · '+p.count+' job mentions" aria-label="'+esc(p.label)+', mentioned in '+p.count+' active job records"><span class="hi-skill-mark">'+skillMark(p.label)+'</span><b>'+esc(p.label)+'</b><small>'+p.count+' jobs</small></div>'
 }).join("")
}
function render(data){countTo($("hiActive"),data.active||0);countTo($("hiEmployers"),data.employers||0);countTo($("hiFreshers"),data.freshers||0);
const cats=Object.fromEntries((data.categories||[]).map(it=>[it.label,it.count]));countTo($("hiIT"),cats.it||0);countTo($("hiInternships"),cats.internship||0);
countTo($("hiArtActive"),data.active||0);countTo($("hiArtCompanies"),data.employers||0);
const updated=$("hiLastUpdated");if(updated)updated.textContent="Current published job data · Verified through "+(data.verifiedThrough||"latest release");
showExperience(data);showEmployers(data);showSkills(data);showCards()}
fetch(prefix+"data/insights-summary.json",{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("Summary fetch failed");return r.json()}).then(render).catch(error=>{console.error("Insights preview data:",error);for(const id of ["hiCompanies","hiSkills"]){const target=$(id);if(target)target.textContent="Published job summary is temporarily unavailable."}showCards()});
})();