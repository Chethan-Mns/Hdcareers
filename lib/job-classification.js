/**
 * Source-aware HD Careers classification.
 * Full-time: minimum accepted experience 0 => fresher; minimum >0 => experienced.
 * Internships and apprenticeships remain distinct regardless of experience.
 * Sales, BPO and support are Non-IT; technical engineering/skills are IT.
 */
const TRAINING=/\b(intern|internship|apprentice|apprenticeship)\b/i;
const NON_IT_ROLE=/\b(bpo|call[ -]?cent(?:er|re)|contact[ -]?cent(?:er|re)|customer[ -]?(?:support|service|care|success)|client[ -]?support|support|service[ -]?desk|help[ -]?desk|sales|business[ -]?development|marketing|recruit(?:ment|er|ing)?|talent[ -]?(?:operations|acquisition)|human[ -]?resources|hr[ -]?(?:associate|executive|recruiter)|billing|collections?|telecaller|voice[ -]?process|non[ -]?voice|back[ -]?office|tax|audit|accounting|finance|operations[ -]?associate|relationship[ -]?manager)\b/i;
const TECHNICAL=/\b(software|developer|development[ -]?engineer|programmer|coding|java(?:script)?|python|c\+\+|c#|typescript|react|angular|node\.?js|sql|nosql|database|backend|front[ -]?end|full[ -]?stack|devops|cloud|aws|azure|databricks|snowflake|pyspark|hadoop|kafka|api|machine[ -]?learning|data[ -]?(?:engineer|scientist|science|analyst)|cyber|network(?:ing)?|linux|computer[ -]?science|information[ -]?technology|qa[ -]?engineer|automation[ -]?engineer|test[ -]?engineer|embedded|electronic(?:s)?|vlsi|cad|design[ -]?engineer|technical)\b/i;
const ENTRY=/\b(freshers?|fresh[ -]?grad(?:uate)?s?|new[ -]?grad(?:uate)?s?|no[ -]?(?:prior[ -]?)?experience|zero[ -]?experience|entry[ -]?level|campus[ -]?(?:hire|hiring|graduate)|graduate[ -]?trainee|university[ -]?graduate)\b/i;
const DURATION=/\b(\d+)\s*(?:[–—-]|to)\s*(\d+)\s*(?:years?|yrs?)\b|\b(\d+)\s*\+?\s*(?:years?|yrs?)\b/gi;

export function isTrainingJob(job={}){
  const cat=String(job.cat||"").toLowerCase();
  return cat==="internship"||cat==="apprenticeship"||TRAINING.test(String(job.role||job.roleTag||""));
}
function numericMinimums(text){
  const years=String(text||"").replace(/\b(?:one|two|three|four)\s+years?\b/gi,m=>
    ({one:"1",two:"2",three:"3",four:"4"})[m.toLowerCase().split(/\s+/)[0]]+" years");
  const found=[];
  for(const m of years.matchAll(DURATION))found.push(Number(m[1]??m[3]));
  return found;
}
export function experienceLevel(job={}){
  const years=String(job.expYears||job.experience||"");
  const role=String(job.role||"");
  const requirements=String(job.elig||"");
  const numeric=numericMinimums(years);
  const evidence=numeric.length?numeric:numericMinimums(requirements);
  if(evidence.length)return Math.min(...evidence)===0?"fresher":"experienced";
  if(/\b(?:less than|under|up to|upto)\s+[1-9]\d*\s*(?:years?|yrs?)\b/i.test(years))return "fresher";
  if(ENTRY.test(years+" "+role))return "fresher";
  const explicit=String(job.expType||"").toLowerCase();
  // A verified, explicitly labelled source can still supply the level when
  // no experience duration appears in the published summary.
  return ["fresher","experienced"].includes(explicit)?explicit:"not-specified";
}
export function jobField(job={}){
  const role=String(job.role||job.roleTag||"");
  if(NON_IT_ROLE.test(role))return "nonit";
  const skills=Array.isArray(job.skills)?job.skills.join(" "):"";
  if(TECHNICAL.test(role+" "+skills))return "it";
  const category=String(job.cat||"").toLowerCase();
  if(category==="nonit"||category==="non-it"||category==="non it")return "nonit";
  if(category==="it")return "it";
  return job.field==="it"?"it":job.field==="nonit"?"nonit":"nonit";
}
export function classifyJob(job={}){
  const cat=String(job.cat||"").toLowerCase();
  const training=isTrainingJob(job);
  const field=jobField(job);
  const expType=experienceLevel(job);
  const effectiveCat=training?(cat==="apprenticeship"||/\bapprentice(ship)?\b/i.test(String(job.role||""))?"apprenticeship":"internship"):
    (["it","nonit","non-it","non it"].includes(cat)?field:cat||field);
  return {cat:effectiveCat,field,expType,training};
}
