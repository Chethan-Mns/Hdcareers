(function(root){
'use strict';
const groups = {
'AWS':['amazon web services'], 'ETL':['extract transform load','extract transformation load'],
'ELT':['extract load transform'], 'SQL':['structured query language'], 'Python':[], 'Snowflake':[],
'Java':[], 'JavaScript':['js','ecmascript'], 'TypeScript':['ts'], 'C++':['cpp'], 'C#':['c sharp','csharp'],
'.NET':['dotnet','dot net'], 'React':['reactjs','react.js'], 'Angular':['angularjs'],
'Node.js':['nodejs','node js'], 'Spring Boot':['springboot'], 'Spring':[],
'HTML':['html5'], 'CSS':['css3'], 'Git':['version control','source control','github','gitlab','bitbucket','svn','mercurial'], 'Linux':[], 'Unix':[],
'Azure':['microsoft azure'], 'GCP':['google cloud','google cloud platform'],
'AWS Glue':['glue'], 'S3':['amazon s3'], 'Redshift':['amazon redshift'], 'EMR':['amazon emr'],
'Lambda':['aws lambda'], 'Kinesis':[], 'EC2':[], 'PySpark':['py spark'], 'Spark':['apache spark'],
'Airflow':['apache airflow'], 'Kafka':['apache kafka'], 'Databricks':[], 'Hadoop':[],
'Docker':[], 'Kubernetes':['k8s'], 'Terraform':[], 'Jenkins':[], 'CI/CD':['ci cd','continuous integration'],
'Power BI':['powerbi'], 'Tableau':[], 'Excel':['microsoft excel'], 'Pandas':[], 'NumPy':[],
'Machine learning':['ml'], 'Artificial intelligence':['ai'], 'Data modeling':['data modelling'],
'Data warehousing':['data warehouse','data warehouses'], 'Data quality':[],
'Data pipelines':['data pipeline'], 'REST':['restful','rest api'], 'APIs':['api','application programming interface'],
'Object-oriented programming':['oop','object oriented programming','object-oriented programming'], 'Data structures':['data structure','dsa'],
'Algorithms':['algorithm','dsa'], 'JSON':['javascript object notation'], 'Problem solving':['problem-solving','problem solving skills'],
'PostgreSQL':['postgres'], 'MySQL':[], 'MongoDB':[], 'Oracle':[], 'SQL Server':['mssql'],
'Salesforce':[], 'Apex':[], 'VMware':[], 'Virtualization':['virtualisation'],
'Testing':['software testing'], 'Selenium':[], 'Automation':[], 'Troubleshooting':[],
'Communication':['communication skills'], 'Customer service':['customer support'],
'Accounting':[], 'Recruitment':[], 'Payroll':[], 'Financial analysis':[], 'SAP':[]
};
function normalize(value){return String(value||'').normalize('NFKC').toLowerCase().replace(/[\u200b-\u200d\ufeff\u00ad]/g,'').replace(/[^a-z0-9+#.]+/g,' ').replace(/\s+/g,' ').trim();}
function locate(text,term){
 const n=normalize(text), t=normalize(term); let start=0;
 while(t && start<=n.length){const i=n.indexOf(t,start);if(i<0)return -1;
 const before=i?n[i-1]:'', after=n[i+t.length]||'';
 if(!/[a-z0-9+#]/.test(before)&&!/[a-z0-9+#]/.test(after))return i;
 start=i+1;}return -1;
}
function aliases(label){return [label,...(groups[label]||[])];}
function extract(profile){
 const jd=[profile.role,profile.description,profile.eligibility,...(profile.skills||[]),...(profile.responsibilities||[])].join('\n');
 const found=Object.keys(groups).filter(k=>aliases(k).some(a=>locate(jd,a)>=0));
 // Preserve unfamiliar explicit skills rather than silently omitting them.
 for(const phrase of profile.skills||[]){
  for(const part of String(phrase).split(/\s*(?:,|;|\s+and\s+|\s+or\s+|\s+\/\s+)\s*/i)){
   const p=part.trim();if(p && !found.some(k=>aliases(k).some(a=>locate(p,a)>=0))&&!/^(not specified|n\/a)$/i.test(p))found.push(p);
  }
 }
 return [...new Set(found)];
}
function analyze(profile,text){
 const keywords=extract(profile);
 const evidence=keywords.map(keyword=>{
  const alias=aliases(keyword).find(a=>locate(text,a)>=0);
  const line=alias?String(text).split(/[\r\n]+/).find(l=>locate(l,alias)>=0):'';
  const source=line||String(text); const pos=alias?locate(source,alias):-1;
  // Normalized excerpts keep PDF whitespace differences from hiding evidence.
  const excerpt=alias?normalize(source).slice(Math.max(0,pos-65),pos+normalize(alias).length+100):'';
  return {keyword,matched:!!alias,alias:alias||'',excerpt};
 });
 const matched=evidence.filter(x=>x.matched).map(x=>x.keyword);
 return {keywords,matched,missing:evidence.filter(x=>!x.matched).map(x=>x.keyword),evidence,
 score:keywords.length?Math.round(100*matched.length/keywords.length):null};
}
const api={normalize,locate,extract,analyze};
if(typeof module!=='undefined'&&module.exports)module.exports=api;
root.ResumeKeywords=api;
})(typeof window!=='undefined'?window:globalThis);
