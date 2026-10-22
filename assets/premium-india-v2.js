/* Premium HD Careers India dashboard. Data strictly sourced from embedded verified cityPins. */
(()=>{"use strict";
const get=id=>document.getElementById(id),number=n=>Number(n||0).toLocaleString("en-IN");
const parser=get("hd-map-data");let raw;
try{raw=JSON.parse(parser?.textContent||"{}")}catch{raw={}}
const pins=(Array.isArray(raw.cityPins)?raw.cityPins:[]).filter(p=>p&&typeof p.city==="string"&&Number.isInteger(p.count)&&p.count>0&&Number.isFinite(p.lat)&&Number.isFinite(p.lng));
const sorted=[...pins].sort((a,b)=>b.count-a.count||a.city.localeCompare(b.city)),total=pins.reduce((n,p)=>n+p.count,0);
const prefix=document.body.dataset.prefix||"";
const safeCityLink=p=>prefix+"index.html?location="+encodeURIComponent(p.city)+"#resultsSection";
const regionKeys=["South","West","North","East","Central"],regions={
South:new Set(["Bengaluru","Bangalore","Hyderabad","Chennai","Madurai","Kochi","Coimbatore","Mysuru","Thiruvananthapuram","Vijayawada","Visakhapatnam"]),
West:new Set(["Mumbai","Navi Mumbai","Pune","Ahmedabad","Surat","Vadodara","Thane"]),
North:new Set(["Gurugram","Gurgaon","Noida","Delhi","New Delhi","Mohali","Jaipur","Saharanpur","Chandigarh","Lucknow"]),
East:new Set(["Kolkata","Bhubaneswar","Patna","Ranchi","Guwahati"]),
Central:new Set(["Indore","Nagpur","Bhopal","Raipur"])
};
const regionTotals=new Map([...regionKeys,"Other"].map(k=>[k,0]));
for(const pin of pins){const key=regionKeys.find(k=>regions[k].has(pin.city))||"Other";regionTotals.set(key,regionTotals.get(key)+pin.count)}
const percent=n=>total?(100*n/total).toFixed(0)+"%":"0%";
const labels={"South":"South India","West":"West India","North":"North India","East":"East India","Central":"Central India","Other":"Other cities"};
const colors={"South":"#0858db","West":"#387ff4","North":"#6ca7ff","East":"#a4cafa","Central":"#d1e4ff","Other":"#8495b1"};
function setText(node,text){if(node)node.textContent=text}
function cityItem(p,i,compact=false){const a=document.createElement("a");a.href=safeCityLink(p);a.className=compact?"hdm-city-card":"hdm-bar";a.setAttribute("aria-label","Find "+p.count+" HD Careers jobs in "+p.city);
 if(compact){const icon=document.createElement("span");icon.className="hdm-city-art";icon.setAttribute("aria-hidden","true");icon.textContent=["▥","▤","▧","▦","▥"][i%5];const content=document.createElement("span");content.className="hdm-city-card-copy";const name=document.createElement("b");name.textContent=p.city;const amount=document.createElement("small");amount.textContent=p.count+" "+(p.count===1?"listing":"listings");content.append(name,amount);const rank=document.createElement("em");rank.textContent="#"+(i+1);a.append(icon,content,rank)}
 else{const rank=document.createElement("span");rank.className="hdm-rank";rank.textContent=String(i+1);const name=document.createElement("strong");name.className="hdm-bar-city";name.textContent=p.city;const track=document.createElement("span");track.className="hdm-bar-track";const fill=document.createElement("span");fill.className="hdm-bar-fill";fill.style.width=(100*p.count/Math.max(1,sorted[0].count)).toFixed(1)+"%";track.append(fill);const count=document.createElement("b");count.className="hdm-bar-value";count.textContent=p.count;a.append(rank,name,track,count)}
 return a}
function update(widget){if(!total)return;
 widget.querySelectorAll("[data-hdm-total]").forEach(el=>setText(el,number(total)));
 widget.querySelectorAll("[data-hdm-cities]").forEach(el=>setText(el,number(pins.length)));
 widget.querySelectorAll("[data-hdm-leader]").forEach(el=>setText(el,sorted[0].city));
 widget.querySelectorAll("[data-hdm-leader-count]").forEach(el=>setText(el,number(sorted[0].count)));
 widget.querySelectorAll("[data-hdm-share]").forEach(el=>setText(el,percent(sorted[0].count)));
 widget.querySelectorAll("[data-hdm-runnerup]").forEach(el=>setText(el,sorted.slice(1,3).map(p=>p.city+" ("+p.count+")").join(" and ")));
 widget.querySelectorAll("[data-hdm-other]").forEach(el=>setText(el,number(total-sorted[0].count)));
 const bars=widget.querySelector("[data-hdm-bars]");if(bars){bars.replaceChildren();sorted.slice(0,widget.classList.contains("hdm-insights")?7:6).forEach((p,i)=>bars.append(cityItem(p,i)))}
 const cities=widget.querySelector("[data-hdm-citycards]");if(cities){cities.replaceChildren();sorted.slice(0,6).forEach((p,i)=>cities.append(cityItem(p,i,true)))}
 const ring=widget.querySelector("[data-hdm-ring]"),legend=widget.querySelector("[data-hdm-regions]");
 if(ring&&legend){const present=[...regionTotals].filter(([,v])=>v>0);let angle=0;ring.style.background="conic-gradient("+present.map(([k,value])=>{const last=angle;angle+=100*value/total;return colors[k]+" "+last.toFixed(2)+"% "+angle.toFixed(2)+"%"}).join(",")+")";legend.replaceChildren();for(const [key,count]of present){const row=document.createElement("div");row.className="hdm-region";const dot=document.createElement("i");dot.style.background=colors[key];dot.setAttribute("aria-hidden","true");const name=document.createElement("span");name.textContent=labels[key];const value=document.createElement("b");value.textContent=number(count);row.append(dot,name,value);legend.append(row)}}
 const set=widget.querySelector("[data-hdm-local-note]");if(set)set.textContent="Counts reflect "+number(total)+" active listings with one identified Indian city. Updated with approved job publishing.";
}
for(const widget of document.querySelectorAll(".hdm-widget"))update(widget);
// Navigation and focus work even if the heavyweight India SVG is still loading.
const more=document.querySelectorAll("[data-hdm-viewall]");
for(const button of more)button.addEventListener("click",()=>{location.assign(prefix+"index.html#resultsSection")});
// Decorative entrance never hides server-rendered content or requires IntersectionObserver.
const reduced=matchMedia("(prefers-reduced-motion: reduce)").matches;
const slow=document.documentElement.classList.contains("hd-lite")||navigator.connection?.saveData||(navigator.deviceMemory&&navigator.deviceMemory<=4);
if(!reduced&&!slow&&"IntersectionObserver" in window){const targets=[...document.querySelectorAll(".hdm-widget .hdm-card,.hdm-widget .hdm-map-surface")];const obs=new IntersectionObserver(items=>{for(const item of items)if(item.isIntersecting){item.target.classList.add("hdm-animate");obs.unobserve(item.target)}},{rootMargin:"60px 0px",threshold:.06});targets.forEach(e=>obs.observe(e))}
})();