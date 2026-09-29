(function(root){
'use strict';
const K=typeof module!=='undefined'&&module.exports?require('./resume-keywords.js'):root.ResumeKeywords;
function minimum(text){const s=String(text||'');if(/not specified/i.test(s))return null;const m=s.match(/(\d+(?:\.\d+)?)\s*(?:\+|[-–]\s*\d+)?\s*(?:years?|yrs?)/i);return m?+m[1]:/fresher|entry.level/i.test(s)?0:null;}
function relevant(profile,text){
 const normalized=K.normalize(text);
 const role=K.normalize(profile.role).replace(/\b(senior|junior|associate|lead| i| ii| iii| iv)\b/g,' ').trim();
 if(role.length>4&&K.locate(normalized,role)>=0)return true;
 const generic=new Set(['engineer','developer','analyst','associate','senior','junior','lead','role','technology','support','data','software']);
 const roleTerms=role.split(/\s+/).filter(x=>x.length>2&&!generic.has(x));
 const coreTerms=role.split(/\s+/).filter(x=>x.length>2&&!['senior','junior','associate','lead'].includes(x));
 if(coreTerms.length&&coreTerms.filter(x=>normalized.includes(x)).length>=Math.min(2,coreTerms.length))return true;
 if(roleTerms.length&&roleTerms.filter(x=>normalized.includes(x)).length>=Math.min(1,roleTerms.length))return true;
 const ks=K.analyze(profile,text).matched;
 return ks.filter(x=>!['Communication','Excel','Testing','Automation'].includes(x)).length>=2;
}
function parseDateToken(raw,now){
 const s=String(raw||'').trim().replace(/\./g,'');
 let m=s.match(/^(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{4})$/i);
 if(m){const idx=['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'].indexOf(m[1].slice(0,3).toLowerCase());return Date.UTC(+m[2],idx,1)}
 m=s.match(/^(\d{1,2})[/-](\d{4})$/);if(m)return Date.UTC(+m[2],Math.max(0,Math.min(11,+m[1]-1)),1);
 m=s.match(/^(\d{4})[/-](\d{1,2})$/);if(m)return Date.UTC(+m[1],Math.max(0,Math.min(11,+m[2]-1)),1);
 m=s.match(/^(\d{4})$/);if(m)return Date.UTC(+m[1],0,1);
 return NaN;
}
function experience(profile,text,now=new Date()){
 const required=minimum(profile.experience);const evidence=[];let stated=null;const raw=String(text);
 for(const sentence of raw.split(/[\n;]+|(?<=[.!?])\s+/)){
  const m=sentence.match(/(\d+(?:\.\d+)?)\s*\+?\s*(years?|yrs?|months?)\b/i);
  if(m&&relevant(profile,sentence)&&/experience|worked|working|engineer|developer|analyst|built|developed/i.test(sentence)){
   const years=+m[1]/(/^month/i.test(m[2])?12:1);
   if(years<50){stated=stated===null?years:Math.max(stated,years);evidence.push(sentence.trim());}
  }
 }
 const month='(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)';
 const date='(?:'+month+'\\s+\\d{4}|\\d{1,2}[/-]\\d{4}|\\d{4}[/-]\\d{1,2}|\\d{4})';
 const rx=new RegExp('('+date+')\\s*(?:-|–|—|to|until)\\s*('+date+'|present|current|now)','gi');
 const matches=[...raw.matchAll(rx)], ranges=[];
 for(const m of matches){
  const start=parseDateToken(m[1],now),end=/present|current|now/i.test(m[2])?now.getTime():parseDateToken(m[2],now);
  const block=raw.slice(Math.max(0,m.index-240),Math.min(raw.length,m.index+m[0].length+240));
  if(Number.isFinite(start)&&Number.isFinite(end)&&end>start&&end<=now.getTime()&&relevant(profile,block)&&!/education|university|bachelor|master|college|graduat(?:e|ion)/i.test(block)){
   ranges.push([start,end]);evidence.push(`${m[1]} - ${m[2]} • ${block.replace(/\s+/g,' ').trim()}`);
  }
 }
 ranges.sort((a,b)=>a[0]-b[0]);const merged=[];
 for(const r of ranges){const last=merged[merged.length-1];if(last&&r[0]<=last[1])last[1]=Math.max(last[1],r[1]);else merged.push([...r]);}
 const dated=merged.length?merged.reduce((n,r)=>n+r[1]-r[0],0)/(365.25*86400000):null;
 const years=dated===null?stated:stated===null?dated:Math.min(stated,dated);
 return {required,years:years===null?null:Math.round(years*10)/10,score:required===null?null:required===0?100:years===null?0:Math.min(100,Math.round(years/required*100)),evidence,uncertain:required>0&&years===null};
}
function degree(text){
 const s=String(text).toLowerCase();
 if(/\b(ph\.?d|doctorate)\b/.test(s))return 3;
 if(/\b(master|masters|m\.?\s?tech|mba|mca|m\.?\s?sc|postgraduate)\b/.test(s))return 2;
 if(/\b(bachelor|bachelors|b\.?\s?tech|b\.?\s?e\.?|bsc|b\.?\s?sc|bca|undergraduate|graduate engineer)\b/.test(s))return 1;
 return 0;
}
function qualification(profile,text){
 const requirement=[profile.education,profile.eligibility].join(' ');
 const need=degree(requirement),found=degree(text);
 const alternatives=/\bor\b|\//i.test(requirement)&&/bachelor|b\.?\s?tech/i.test(requirement);
 const minimumDegree=alternatives?1:need;
 return {score:minimumDegree?found>=minimumDegree?100:0:null,need:minimumDegree,found,note:minimumDegree?(found>=minimumDegree?'Degree level detected; check field, grades and other conditions.':'Required degree level not detected.'): 'No supported degree requirement detected; excluded from overall.'};
}
function assess(profile,text){
 const keywords=K.analyze(profile,text),exp=experience(profile,text),qual=qualification(profile,text);
 const parts=[[keywords.score,.5],[exp.score,.3],[qual.score,.2]].filter(x=>x[0]!==null);
 const weight=parts.reduce((n,x)=>n+x[1],0);
 return {keywords,exp,qual,overall:weight?Math.round(parts.reduce((n,x)=>n+x[0]*x[1],0)/weight):null};
}
const api={assess,experience,qualification,minimum};if(typeof module!=='undefined'&&module.exports)module.exports=api;
root.ResumeAssessment=api;
})(typeof window!=='undefined'?window:globalThis);
