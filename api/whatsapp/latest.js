import fs from "node:fs";
import path from "node:path";

const SITE_BASE="https://hdcareers.in/";
const WHATSAPP_CHANNEL="https://whatsapp.com/channel/0029VbAxOna7NoZvhuKX362z";
const TELEGRAM_CHANNEL="https://t.me/HD_Careers";

const DEGREE_PATTERNS=[
  /\bB\.?E\.?\s*\/?\s*B\.?Tech\b/i,
  /\bB\.?Tech\b/i,
  /\bM\.?Tech\b/i,
  /\bMCA\b/i,
  /\bBCA\b/i,
  /\bMBA\b/i,
  /\bB\.?Sc\b/i,
  /\bM\.?Sc\b/i,
  /\bDiploma\b/i,
  /\bBachelor(?:'s)?(?: degree)?\b/i,
  /\bMaster(?:'s)?(?: degree)?\b/i,
  /\bGraduate\b/i,
  /\bPostgraduate\b/i
];

function readJobs(){
  const file=path.join(process.cwd(),"data","jobs.json");
  const data=JSON.parse(fs.readFileSync(file,"utf8"));
  if(!Array.isArray(data))throw new Error("Job data is unavailable.");
  return data;
}

function qualification(job){
  const explicit=String(job.qualification||"").trim();
  if(explicit)return explicit;

  const elig=String(job.elig||"").replace(/\s+/g," ").trim();
  if(!elig)return "Not specified in official posting";
  if(/does not specify (?:a )?(?:degree|qualification)|qualification (?:is )?not specified|degree (?:is )?not specified/i.test(elig)){
    return "Not specified in official posting";
  }

  const found=[];
  for(const re of DEGREE_PATTERNS){
    const m=elig.match(re);
    if(m&&!found.some(x=>x.toLowerCase()===m[0].toLowerCase()))found.push(m[0]);
  }
  return found.length?found.join(" / "):"Not specified in official posting";
}

function disclosed(value){
  const s=String(value||"").trim();
  return s&&!/^(not disclosed|not specified|n\/?a|na)$/i.test(s);
}

function message(job){
  const lines=[
    `${job.company} is Hiring ✅`,
    "",
    `*Role:* ${job.role}`
  ];

  if(String(job.expType||"").toLowerCase()==="fresher"){
    lines.push(`*Batch:* ${disclosed(job.batch)?job.batch:"Not specified"}`);
  }

  lines.push(`*Qualification:* ${qualification(job)}`);

  if(String(job.expType||"").toLowerCase()==="experienced"&&disclosed(job.expYears)){
    lines.push(`*Experience:* ${job.expYears}`);
  }

  lines.push(`*Location:* ${job.loc||"Not specified"}`);

  if(disclosed(job.salary))lines.push(`*Package:* ${job.salary}`);

  const page=String(job.page||"").replace(/^\/+/, "");
  const apply=page?SITE_BASE+page:String(job.apply||"");

  lines.push(
    "",
    `Apply Link: ${apply}`,
    "",
    `𝗝𝗼𝗶𝗻 𝗢𝘂𝗿 𝗪𝗵𝗮𝘁𝘀𝗔𝗽𝗽: ${WHATSAPP_CHANNEL}`,
    `𝗝𝗼𝗶𝗻 𝗢𝘂𝗿 𝗧𝗲𝗹𝗲𝗴𝗿𝗮𝗺: ${TELEGRAM_CHANNEL}`
  );

  return lines.join("\n");
}

export default async function handler(req,res){
  res.setHeader("Cache-Control","no-store, max-age=0");
  res.setHeader("Access-Control-Allow-Origin","*");

  if(req.method!=="GET"){
    res.setHeader("Allow","GET");
    return res.status(405).json({error:"Method not allowed."});
  }

  try{
    const jobs=readJobs();
    const rawId=String(req.query?.id||"").trim();
    const offset=Math.max(0,Math.min(50,Number.parseInt(String(req.query?.offset||"0"),10)||0));

    let job=null;
    if(rawId)job=jobs.find(x=>String(x.id)===rawId)||null;
    else job=jobs[offset]||null;

    if(!job)return res.status(404).json({error:"Job not found."});

    const text=message(job);
    if(String(req.query?.format||"text").toLowerCase()==="json"){
      return res.status(200).json({
        ok:true,
        id:job.id,
        company:job.company,
        role:job.role,
        page:SITE_BASE+String(job.page||"").replace(/^\/+/, ""),
        text
      });
    }

    res.setHeader("Content-Type","text/plain; charset=utf-8");
    return res.status(200).send(text);
  }catch(error){
    return res.status(500).json({error:error?.message||"Could not prepare WhatsApp post."});
  }
}
