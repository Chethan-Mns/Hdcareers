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
function showSkills(d){const root=$("hiSkills"),items=(d.topSkills||[]).slice(0,10);if(!items.length){root.innerHTML='<p class="hi-empty">Skill data is not available.</p>';return}const max=Math.max(1,items[0].count);
root.innerHTML=items.map((p,i)=>{const size=Math.max(94,Math.min(128,94+34*p.count/max));return '<span class="hi-skill" style="--size:'+size.toFixed(0)+'px;--step:'+i+';--drift:'+(i%3+3)+'s" title="'+esc(p.label)+": "+p.count+' job mentions"><b>'+esc(p.label)+'</b><small>'+p.count+'</small></span>'}).join("")}
function showCities(d){const arr=(d.cityPins||[]).filter(p=>Number.isFinite(p.count)&&p.count>0),total=arr.reduce((v,p)=>v+p.count,0);
if(!arr.length){$("hiCityLegend").innerHTML='<p class="hi-empty">Location data not yet available.</p>';return}
const top=arr.slice(0,5).map(p=>({label:p.city,count:p.count})),rest=total-top.reduce((v,p)=>v+p.count,0);
if(rest>0)top.push({label:"Other cities",count:rest});
$("hiCityRing").style.background=ringGradient(top);countTo($("hiCityTotal"),total);
$("hiCityLegend").innerHTML=top.map((p,i)=>'<button type="button" class="hi-city-legend-row" '+(p.label==="Other cities"?'disabled':'data-city="'+esc(p.label)+'"')+' aria-label="'+esc(p.label)+", "+p.count+' mapped jobs"><span class="hi-legend-dot" style="background:'+colors[i]+'"></span><span>'+esc(p.label)+'</span><b>'+p.count+'</b></button>').join("");
$("hiCityLegend").querySelectorAll("[data-city]").forEach(b=>b.addEventListener("click",()=>location.assign(prefix+"index.html?location="+encodeURIComponent(b.dataset.city))))}
function render(data){countTo($("hiActive"),data.active||0);countTo($("hiEmployers"),data.employers||0);countTo($("hiFreshers"),data.freshers||0);
const cats=Object.fromEntries((data.categories||[]).map(it=>[it.label,it.count]));countTo($("hiIT"),cats.it||0);countTo($("hiInternships"),cats.internship||0);
countTo($("hiArtActive"),data.active||0);countTo($("hiArtCompanies"),data.employers||0);
const updated=$("hiLastUpdated");if(updated)updated.textContent="Current published job data · Verified through "+(data.verifiedThrough||"latest release");
showExperience(data);showEmployers(data);showSkills(data);showCities(data);showCards()}
fetch(prefix+"data/insights-summary.json",{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("Summary fetch failed");return r.json()}).then(render).catch(error=>{console.error("Insights preview data:",error);for(const id of ["hiCompanies","hiSkills","hiCityLegend"]){const target=$(id);if(target)target.textContent="Published job summary is temporarily unavailable."}showCards()});
})();