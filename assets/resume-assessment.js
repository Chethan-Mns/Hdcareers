(function(root){
'use strict';
const K=typeof module!=='undefined'&&module.exports?require('./resume-keywords.js'):root.ResumeKeywords;

function minimum(text){
 const s=String(text||'');
 if(/not specified|not disclosed|n\/a/i.test(s))return null;
 const m=s.match(/(\d+(?:\.\d+)?)\s*(?:\+|[-–]\s*\d+)?\s*(?:years?|yrs?)/i);
 if(m)return +m[1];
 return /fresher|entry.level|no experience|0\s*(?:years?|yrs?)/i.test(s)?0:null;
}

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

function parseDateToken(raw){
 const s=String(raw||'').trim().replace(/\./g,'');
 let m=s.match(/^(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{4})$/i);
 if(m){
  const idx=['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'].indexOf(m[1].slice(0,3).toLowerCase());
  return Date.UTC(+m[2],idx,1);
 }
 m=s.match(/^(\d{1,2})[/-](\d{4})$/);if(m)return Date.UTC(+m[2],Math.max(0,Math.min(11,+m[1]-1)),1);
 m=s.match(/^(\d{4})[/-](\d{1,2})$/);if(m)return Date.UTC(+m[1],Math.max(0,Math.min(11,+m[2]-1)),1);
 m=s.match(/^(\d{4})$/);if(m)return Date.UTC(+m[1],0,1);
 return NaN;
}

function headingType(line){
 const s=String(line||'').trim().replace(/[:|]+$/,'').toLowerCase().replace(/\s+/g,' ');
 if(!s||s.length>64)return null;
 if(/^(work experience|professional experience|employment|employment history|work history|career history|experience|professional background)$/.test(s))return'work';
 if(/^(education|academic background|academics|educational qualifications?|academic qualifications?)$/.test(s))return'education';
 if(/^(projects?|academic projects?|personal projects?|skills?|technical skills?|certifications?|certificates?|achievements?|awards?|languages?|summary|profile|objective|interests?|publications?|volunteering|extracurriculars?)$/.test(s))return'other';
 return null;
}

function professionalText(raw){
 const lines=String(raw||'').replace(/\r/g,'').split('\n');
 let mode=null,foundWorkHeading=false;
 const work=[];
 for(const line of lines){
  const h=headingType(line);
  if(h){mode=h;if(h==='work')foundWorkHeading=true;continue;}
  if(mode==='work')work.push(line);
 }
 const joined=work.join('\n').trim();
 return {text:foundWorkHeading&&joined?joined:String(raw||''),strict:!foundWorkHeading};
}

function statedExperience(profile,text){
 let best=null;
 const evidence=[];
 const pieces=String(text||'').split(/[\n;]+|(?<=[.!?])\s+/);
 const patterns=[
  /(\d+(?:\.\d+)?)\s*\+?\s*(years?|yrs?|months?)\s+(?:of\s+)?(?:relevant\s+|professional\s+|work\s+|industry\s+|total\s+)?experience\b/i,
  /(?:relevant\s+|professional\s+|work\s+|industry\s+|total\s+)?experience\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*\+?\s*(years?|yrs?|months?)\b/i,
  /(?:worked|working|employed)\s+(?:for\s+)?(\d+(?:\.\d+)?)\s*\+?\s*(years?|yrs?|months?)\b/i
 ];
 for(const piece of pieces){
  if(!relevant(profile,piece))continue;
  if(/\b(education|university|college|school|b\.?\s?tech|bachelor|master|degree|cgpa|gpa|graduat(?:e|ion))\b/i.test(piece)&&!/work|professional|employment|experience/i.test(piece))continue;
  for(const rx of patterns){
   const m=piece.match(rx);if(!m)continue;
   const years=+m[1]/(/^month/i.test(m[2])?12:1);
   if(years>=0&&years<50){
    best=best===null?years:Math.max(best,years);
    evidence.push(piece.trim());
   }
   break;
  }
 }
 return {years:best,evidence};
}

function experience(profile,text,now=new Date()){
 const required=minimum(profile.experience);
 const source=professionalText(text);
 const stated=statedExperience(profile,source.text);
 const raw=source.text;
 const evidence=[...stated.evidence];
 const month='(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)';
 const date='(?:'+month+'\\s+\\d{4}|\\d{1,2}[/-]\\d{4}|\\d{4}[/-]\\d{1,2}|\\d{4})';
 const rx=new RegExp('('+date+')\\s*(?:-|–|—|to|until)\\s*('+date+'|present|current|now)','gi');
 const ranges=[];
 for(const m of raw.matchAll(rx)){
  const start=parseDateToken(m[1]);
  const end=/present|current|now/i.test(m[2])?now.getTime():parseDateToken(m[2]);
  const local=raw.slice(Math.max(0,m.index-120),Math.min(raw.length,m.index+m[0].length+160));
  const workContext=/\b(worked|working|employed|employment|experience|developer|analyst|consultant|specialist|manager|associate|intern|trainee|architect|administrator|scientist|designer|lead)\b/i.test(local)||relevant(profile,local);
  const educationContext=/\b(education|university|college|school|b\.?\s?tech|bachelor|master|degree|cgpa|gpa|graduat(?:e|ion)|academic)\b/i.test(local);
  if(!Number.isFinite(start)||!Number.isFinite(end)||end<=start||end>now.getTime())continue;
  if(!workContext)continue;
  if(source.strict&&educationContext&&!/\b(worked|working|employed|employment|professional experience|work experience|developer|analyst|consultant|specialist|manager|associate|intern|trainee)\b/i.test(local))continue;
  ranges.push([start,end]);
  evidence.push((m[1]+' - '+m[2]+' • '+local.replace(/\s+/g,' ').trim()));
 }
 ranges.sort((a,b)=>a[0]-b[0]);
 const merged=[];
 for(const r of ranges){
  const last=merged[merged.length-1];
  if(last&&r[0]<=last[1])last[1]=Math.max(last[1],r[1]);else merged.push([...r]);
 }
 const dated=merged.length?merged.reduce((n,r)=>n+r[1]-r[0],0)/(365.25*86400000):null;
 const years=dated===null?stated.years:stated.years===null?dated:Math.min(stated.years,dated);
 const rounded=years===null?null:Math.round(years*10)/10;
 const score=required===null||required===0?null:rounded===null?0:Math.min(100,Math.round(rounded/required*100));
 return {
  required,
  years:rounded,
  score,
  evidence,
  uncertain:required>0&&rounded===null,
  requirementType:required===null?'not-specified':required===0?'entry-level':'minimum'
 };
}

function degree(text){
 const s=String(text||'').toLowerCase();
 if(/\b(ph\.?d|doctorate)\b/.test(s))return 3;
 if(/\b(master|masters|m\.?\s?tech|mba|mca|m\.?\s?sc|postgraduate)\b/.test(s))return 2;
 if(/\b(bachelor|bachelors|b\.?\s?tech|b\.?\s?e\.?|bsc|b\.?\s?sc|bca|undergraduate|graduate engineer)\b/.test(s))return 1;
 return 0;
}

function degreeLabel(level){
 return level>=3?'Doctorate':level===2?"Master's":level===1?"Bachelor's":'Not detected';
}

function qualification(profile,text){
 const requirement=[profile.education,profile.eligibility].join(' ');
 const need=degree(requirement),found=degree(text);
 const alternatives=(/\bor\b/i.test(requirement)||/\//.test(requirement))&&/bachelor|b\.?\s?tech/i.test(requirement);
 const minimumDegree=alternatives?1:need;
 const score=minimumDegree?found>=minimumDegree?100:0:null;
 return {
  score,
  need:minimumDegree,
  found,
  needLabel:minimumDegree?degreeLabel(minimumDegree):'Not specified',
  foundLabel:found?degreeLabel(found):'Not detected',
  note:minimumDegree?(found>=minimumDegree?'Qualification requirement matched.':'Required qualification was not confidently detected.'):'No specific degree requirement detected.'
 };
}

function assess(profile,text){
 const keywords=K.analyze(profile,text),exp=experience(profile,text),qual=qualification(profile,text);
 const parts=[[keywords.score,.5],[exp.score,.3],[qual.score,.2]].filter(x=>x[0]!==null);
 const weight=parts.reduce((n,x)=>n+x[1],0);
 return {keywords,exp,qual,overall:weight?Math.round(parts.reduce((n,x)=>n+x[0]*x[1],0)/weight):null};
}

const api={assess,experience,qualification,minimum};
if(typeof module!=='undefined'&&module.exports)module.exports=api;
root.ResumeAssessment=api;
})(typeof window!=='undefined'?window:globalThis);
