(()=>{"use strict";
const ids=["hdpLocationMap","hiLocationMap"];
const nodes=ids.map(id=>document.getElementById(id)).filter(Boolean);if(!nodes.length)return;
const prefix=document.body.dataset.prefix||"";
const feed=prefix+"data/insights-summary.json";let loading=null,summaryPromise=null;
const H="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",S="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
function loadLeaflet(){if(window.L)return Promise.resolve(window.L);if(loading)return loading;
loading=new Promise((resolve,reject)=>{
 if(!document.querySelector('link[data-hd-leaflet]')){const l=document.createElement("link");l.rel="stylesheet";l.href=H;l.dataset.hdLeaflet="true";document.head.appendChild(l)}
 const script=document.createElement("script");script.src=S;script.async=true;script.onload=()=>window.L?resolve(window.L):reject(Error("Map library unavailable"));script.onerror=()=>reject(Error("Map library download failed"));document.head.appendChild(script)
});return loading}
function getSummary(){if(!summaryPromise)summaryPromise=fetch(feed,{cache:"no-store",credentials:"omit"}).then(r=>{if(!r.ok)throw Error("Map data unavailable");return r.json()});return summaryPromise}
function text(node,value){if(node)node.textContent=String(value)}
function buildMap(container,L,data){
const canvas=container.querySelector(".hd-map-canvas");if(!canvas)return;
const pins=Array.isArray(data.cityPins)?data.cityPins.filter(p=>Number.isFinite(p.lat)&&Number.isFinite(p.lng)&&Number.isInteger(p.count)&&p.count>0&&p.city):[];
if(!pins.length){canvas.innerHTML='<div class="hd-map-fallback">City-level job locations are not yet available.</div>';return}
const small=container.id==="hdpLocationMap";const map=L.map(canvas,{scrollWheelZoom:false,zoomControl:true,attributionControl:true,preferCanvas:true,worldCopyJump:false}).setView([22.3,79.0],small?4.4:5);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:17,minZoom:3,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a>'}).addTo(map);
const esc=s=>String(s||"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
for(const p of pins){const icon=L.divIcon({className:"",html:'<div class="hd-map-pulse" aria-label="'+esc(p.city)+': '+p.count+' jobs">'+p.count+'</div>',iconSize:[38,38],iconAnchor:[19,19]});const marker=L.marker([p.lat,p.lng],{icon,title:p.city+": "+p.count+" active listings"}).addTo(map);marker.bindPopup('<strong>'+esc(p.city)+'</strong><div>'+p.count+' Active listing'+(p.count===1?'':'s')+' with an unambiguous city location</div>')}
const title=container.querySelector("[data-hd-map-title]");text(title,pins.length+" mapped cities · "+pins.reduce((n,p)=>n+p.count,0)+" single-city listings");
const legend=container.parentElement.querySelector(".hd-map-legend");if(legend)legend.innerHTML=pins.slice(0,6).map(p=>'<span>'+esc(p.city)+' <b>'+p.count+'</b></span>').join("");
requestAnimationFrame(()=>map.invalidateSize());setTimeout(()=>map.invalidateSize(),220);
}
function init(node){const c=node.querySelector(".hd-map-canvas");if(!c)return;c.innerHTML='<div class="hd-map-fallback">Loading mapped job locations…</div>';
Promise.all([loadLeaflet(),getSummary()]).then(([L,data])=>{c.replaceChildren();buildMap(node,L,data)}).catch(err=>{console.warn("HD Careers India map",err);c.innerHTML='<div class="hd-map-fallback">The interactive map could not load. Location statistics are available in the cards above.</div>'})}
if("IntersectionObserver" in window){const io=new IntersectionObserver(entries=>{for(const e of entries){if(e.isIntersecting){io.unobserve(e.target);init(e.target)}}},{rootMargin:"280px"});nodes.forEach(n=>io.observe(n))}else nodes.forEach(init);
})();