(function(root){
'use strict';
const K=typeof module!=='undefined'&&module.exports?require('./resume-keywords.js'):root.ResumeKeywords;
function minimum(text){const s=String(text||'');if(/not specified/i.test(s))return null;const m=s.match(/(\d+(?:\.\d+)?)\s*(?:\+|[-–]\s*\d+)?\s*(?:years?|yrs?)/i);return m?+m[1]:/fresher|entry.level/i.test(s)?0:null;}
function relevant(profile,text){
 const role=K.normalize(profile.role).replace(/\b(senior|junior|associate|lead| i| ii)\b/g,'').trim();
 if(role.length>4&&K.locate(text,role)>=0)return true;
 const ks=K.analyze(profile,text).matched;
 return ks.filter(x=>!['Communication','Excel','Testing','Automation'].includes(x)).length>=2;
}
function experience(profile,text,now=new Date()){
 const required=minimum(profile.experience);const evidence=[];let stated=null;
 // A duration must be attached to relevant work, not just the largest number in a CV.
 for(const sentence of String(text).split(/[\n;]+|(?<=[.!?])\s+/)){
  const m=sentence.match(/(\d+(?:\.\d+)?)\s*\+?\s*(years?|yrs?|months?)\b/i);
  if(m&&relevant(profile,sentence)&&/experience|worked|working|engineer|developer|analyst|built|developed/i.test(sentence)){
   const years=+m[1]/(/^month/i.test(m[2])?12:1);
   if(years<50){stated=stated===null?years:Math.max(stated,years);evidence.push(sentence.trim());}
  }
 }
 const month='(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)';
 const date=month+'\\s+\\d{4}';const rx=new RegExp('('+date+')\\s*(?:-|–|—|to)\\s*('+date+'|present|current|now)','gi');
 const matches=[...String(text).matchAll(rx)], ranges=[];
 for(let i=0;i<matches.length;i++){
  const m=matches[i],start=Date.parse('1 '+m[1]),end=/present|current|now/i.test(m[2])?now.getTime():Date.parse('1 '+m[2]);
  const block=String(text).slice(Math.max(i?matches[i-1].index+matches[i-1][0].length:0,m.index-100),Math.min(matches[i+1]?.index??text.length,m.index+500));
  if(Number.isFinite(start)&&Number.isFinite(end)&&end>start&&end<=now.getTime()&&relevant(profile,block)&&!/education|university|bachelor|master|college/i.test(block.slice(0,100))){ranges.push([start,end]);evidence.push(block.trim());}
 }
 // Merge overlapping employment periods before counting relevant tenure.
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
 // Alternatives: a bachelor's OR master's permits either degree level.
 const alternatives=/\bor\b|\//i.test(requirement)&&/bachelor|b\.?\s?tech/i.test(requirement);
 const minimumDegree=alternatives?1:need;
 return {score:minimumDegree?found>=minimumDegree?100:0:null,need:minimumDegree,found,
 note:minimumDegree?(found>=minimumDegree?'Degree level detected; check field, grades and other conditions.':'Required degree level not detected.'): 'No supported degree requirement detected; excluded from overall.'};
}
function assess(profile,text){
 const keywords=K.analyze(profile,text),exp=experience(profile,text),qual=qualification(profile,text);
 const parts=[[keywords.score,.5],[exp.score,.3],[qual.score,.2]].filter(x=>x[0]!==null);
 const weight=parts.reduce((n,x)=>n+x[1],0);
 return {keywords,exp,qual,overall:weight?Math.round(parts.reduce((n,x)=>n+x[0]*x[1],0)/weight):null};
}
const api={assess,experience,qualification,minimum};if(typeof module!=='undefined'&&module.exports)module.exports=api;root.ResumeAssessment=api;
})(typeof window!=='undefined'?window:globalThis);
