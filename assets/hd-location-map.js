(()=>{"use strict";
// Simplified India outline from Natural Earth public-domain geography (johan/world.geo.json).
// Viewport projection: coordinates are interpreted in WGS84 longitude/latitude.
const SHAPE="M194.1 36.7 L210 52.2 L208.5 63 L214.5 69.8 L214 76.6 L203.3 74.8 L207.5 89.4 L222.1 97.8 L242.7 107.1 L233.3 113.1 L227.5 125.5 L241.9 130.5 L255.9 137 L275.3 144.4 L295.6 146.1 L304.2 152.9 L315.7 154.1 L333.5 157.2 L345.9 157 L347.6 151.8 L345.6 143.3 L346.8 137.6 L355.8 134.8 L357.1 145.3 L357.4 147.9 L370.9 153 L380.2 150.9 L392.8 151.8 L404.9 151.4 L405.9 143.3 L399.9 139 L411.9 137.4 L425.4 127.5 L442.5 119.1 L455 122.3 L465.5 116.8 L472.5 125 L467.5 130.6 L483.5 132.5 L484.6 137.6 L479.4 140 L480.6 148.1 L470 145.7 L450.8 154.9 L451.3 162.5 L443.1 173.6 L442.3 180.1 L435.7 191 L424.1 188 L423.5 201.7 L420.1 206.2 L421.7 211.8 L414.4 215 L406.6 193.9 L402.5 194 L400 202.4 L391.9 195.6 L396.5 188 L403.1 187.3 L410 176.1 L401.4 173.8 L387.7 174 L373.5 172.2 L372.2 163 L365.1 162.3 L353.4 156.6 L348.1 165.6 L358.8 172.6 L349.5 177.5 L346.3 182.4 L355.4 185.9 L352.9 193.9 L358 203.9 L360.3 214.8 L358.2 219.6 L348.1 219.4 L329.8 222.2 L330.6 232.2 L322.7 240 L301.3 248.9 L284.7 264.5 L273.6 272.9 L258.8 281.5 L258.7 287.6 L251.3 290.9 L238 295.6 L231 296.3 L226.6 306.4 L229.7 323.7 L230.5 334.7 L224.2 347.3 L224.1 369.8 L216.4 370.4 L209.6 380.5 L214.2 384.9 L200.6 388.6 L195.6 397.6 L189.7 401.5 L175.6 389.1 L168.7 370.5 L163 357.2 L157.8 350.9 L149.9 338.2 L146.3 321.6 L143.7 313.3 L130.2 295.1 L124 269.4 L119.6 252.5 L119.6 236.4 L116.8 224 L95.2 232 L84.7 230.4 L65.3 214.3 L72.4 209.5 L68 204.3 L50.6 193.1 L60.5 184.2 L93.2 184.3 L90.2 172.9 L81.9 166.2 L80.2 156 L70.5 150 L86.9 136.1 L104.1 137.2 L119.6 123.3 L128.9 109.8 L143.4 96.5 L143.1 87.1 L155.8 79.4 L143.8 72.9 L138.6 63.9 L133.4 52.3 L140.7 46.6 L163.2 49.8 L179.7 47.8 L194.1 36.7 Z";
const W=550,H=450;
const project=(lon,lat)=>[48+(lon-68)*14.85,30+(36-lat)*13.25];
const ids=["hdpLocationMap","hiLocationMap"],nodes=ids.map(i=>document.getElementById(i)).filter(Boolean);
const ns="http://www.w3.org/2000/svg";
function el(tag,attrs){const n=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs||{}))n.setAttribute(k,String(v));return n}
function staticOutline(parent){const svg=el("svg",{viewBox:"0 0 "+W+" "+H,"aria-label":"Map of India with active job city markers",role:"img",preserveAspectRatio:"xMidYMid meet",class:"hd-india-svg"});
  const defs=el("defs"),gradient=el("linearGradient",{id:"hdIndiaGradient",x1:"0%",y1:"0%",x2:"100%",y2:"100%"});
  const one=el("stop",{offset:"0%","stop-color":"#dadce0"}),two=el("stop",{offset:"100%","stop-color":"#dadce0"});
  gradient.append(one,two);defs.append(gradient);svg.append(defs);
  const bg=el("rect",{width:W,height:H,fill:"#f8f9fa",rx:20});svg.append(bg);
  const states=Array.isArray(window.HD_INDIA_STATE_PATHS)?window.HD_INDIA_STATE_PATHS:[];
  if(states.length>=30){
    const all=el("g",{class:"hd-state-boundaries",role:"group","aria-label":"State and union territory outlines"});
    for(const state of states){const path=el("path",{d:state.d,class:"hd-india-state","data-state":state.n});const tip=el("title");tip.textContent=state.n;path.append(tip);all.append(path)}
    svg.append(all);
  }else{
    svg.append(el("path",{d:SHAPE,fill:"#dadce0",stroke:"#ffffff","stroke-width":"2.2","stroke-linejoin":"round"}));
  }
  const cities=el("g",{class:"hd-india-cities"});svg.append(cities);parent.append(svg);
  return {svg,cities};
}
function draw(container,data){const canvas=container.querySelector(".hd-map-canvas");if(!canvas)return;
  const g=canvas.querySelector(".hd-india-cities");if(!g)return;
  const pins=(Array.isArray(data.cityPins)?data.cityPins:[]).filter(p=>p&&typeof p.city==="string"&&Number.isFinite(p.lat)&&Number.isFinite(p.lng)&&Number.isInteger(p.count)&&p.count>0&&p.lat>=7&&p.lat<=38&&p.lng>=68&&p.lng<=98);
  g.replaceChildren();
  const panel=container.querySelector("[data-hd-map-title]");
  if(panel)panel.textContent=pins.length+" mapped cities · "+pins.reduce((a,p)=>a+p.count,0)+" single-city listings";
  const info=container.querySelector(".hd-india-hover");
  for(const p of pins){
    const [x,y]=project(p.lng,p.lat),count=p.count;
    const marker=el("g",{class:"hd-india-marker",role:"button",tabindex:"0","aria-label":p.city+": "+count+" active jobs"});
    const halo=el("circle",{class:"hd-india-halo",cx:x,cy:y,r:Math.min(33,12+Math.sqrt(count)*2.7)});
    const disk=el("circle",{class:"hd-india-dot",cx:x,cy:y,r:Math.min(28,8+Math.sqrt(count)*2.45)});
    const title=el("title");title.textContent=p.city+" · "+count+" Active "+(count===1?"job":"jobs");
    marker.append(halo,disk,title);
    const show=()=>{if(info){info.hidden=false;info.textContent=p.city+" · "+count+" active "+(count===1?"listing":"listings")}marker.classList.add("hd-selected")};
    const hide=()=>{marker.classList.remove("hd-selected")};
    marker.addEventListener("mouseenter",show);marker.addEventListener("focus",show);marker.addEventListener("mouseleave",hide);marker.addEventListener("blur",hide);
    marker.addEventListener("click",()=>{show();const rail=container.closest(".hdp-map-layout");const b=rail&&[...rail.querySelectorAll(".hdp-map-bar")].find(x=>x.dataset.city===p.city);if(b){b.focus({preventScroll:true})}else if(info){info.scrollIntoView({block:"nearest"})}});
    marker.addEventListener("keydown",event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();show()}});
    g.append(marker);
    if(["Bengaluru","Mumbai","Hyderabad","Gurugram"].includes(p.city)){
      const yy=p.city==="Bengaluru"?y+23:y-13;
      const lab=el("text",{class:"hd-city-label",x:x+12,y:yy,"text-anchor":"start"});
      lab.textContent=p.city+" · "+p.count;
      g.append(lab);
    }
  }
  const layout=container.closest(".hdp-map-layout");
  const dash=layout&&layout.querySelector(".hdp-map-dashboard");
  if(dash){
    const top=pins.slice().sort((a,b)=>b.count-a.count).slice(0,5);
    const total=dash.querySelector("[data-hd-map-total]"),cities=dash.querySelector("[data-hd-map-cities]"),leader=dash.querySelector("[data-hd-map-leader]");
    if(total)total.textContent=pins.reduce((n,p)=>n+p.count,0).toLocaleString("en-IN");
    if(cities)cities.textContent=String(pins.length);
    if(leader&&top[0])leader.textContent=top[0].city+" leads with "+top[0].count+" openings";
    const bars=dash.querySelector(".hdp-map-bars");
    if(bars){bars.replaceChildren();for(const c of top){
      const button=document.createElement("button");button.type="button";button.className="hdp-map-bar";button.dataset.city=c.city;button.title="Browse "+c.city+" jobs";
      const name=document.createElement("span");name.textContent=c.city;
      const rail=document.createElement("span");rail.className="hdp-map-bar-rail";
      const fill=document.createElement("span");fill.className="hdp-map-bar-fill";fill.style.width=(c.count/top[0].count*100).toFixed(1)+"%";rail.append(fill);
      const count=document.createElement("strong");count.className="hdp-map-bar-count";count.textContent=String(c.count);
      button.append(name,rail,count);button.addEventListener("click",()=>{const prefix=document.body.dataset.prefix||"";location.assign(prefix+"index.html?location="+encodeURIComponent(c.city))});bars.append(button);
    }}
  }
  const holder=container.parentElement;let legend=holder&&holder.querySelector(".hd-map-legend");
  if(!legend&&container.nextElementSibling&&container.nextElementSibling.classList.contains("hd-map-legend"))legend=container.nextElementSibling;
  if(legend){legend.replaceChildren();for(const p of pins.slice(0,7)){const span=document.createElement("span");const strong=document.createElement("b");span.textContent=p.city+" ";strong.textContent=String(p.count);span.append(strong);legend.append(span)}}
}
for(const n of nodes){const c=n.querySelector(".hd-map-canvas");if(!c)continue;c.replaceChildren();staticOutline(c);
  const tip=document.createElement("div");tip.className="hd-india-hover";tip.hidden=true;tip.setAttribute("aria-live","polite");n.append(tip);
}
if(!nodes.length)return;
const embedded=document.getElementById("hd-map-data");
if(embedded&&embedded.textContent.trim()){
  try{
    const data=JSON.parse(embedded.textContent);
    if(Array.isArray(data.cityPins)&&data.cityPins.length){nodes.forEach(n=>draw(n,data));return}
  }catch(err){console.warn("Embedded India job map data malformed",err)}
}
// Supplemental fallback for older generated pages; latest previews embed their marker data.
const prefix=document.body.dataset.prefix||"";
fetch(prefix+"data/insights-summary.json",{cache:"no-store",credentials:"same-origin"}).then(r=>{if(!r.ok)throw Error("Stats unavailable");return r.json()}).then(d=>nodes.forEach(n=>draw(n,d))).catch(()=>{nodes.forEach(n=>{const note=n.querySelector("[data-hd-map-title]");if(note)note.textContent="India map outline is available · city data temporarily unavailable";});});
})();