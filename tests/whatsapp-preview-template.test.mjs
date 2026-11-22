import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

// Validate the public text preview without importing the Vercel handler.
const source=fs.readFileSync("api/whatsapp/latest.js","utf8")
  .replace(/^import .*;\s*$/gm,"")
  .split("export default async function handler")[0];
const context={};
vm.runInNewContext(source+"\nthis.formatJob=message;",context,{timeout:1000});
const formatJob=context.formatJob;

test("Brillio preview matches the owner-approved WhatsApp format",()=>{
  const job={
    company:"Brillio",
    role:"Associate Engineer, Applications & Platforms",
    loc:"Chennai, Tamil Nadu, India",
    expYears:"Entry level; up to 2 years",
    field:"it",
    page:"jobs/brillio-associate-engineer-applications-platforms.html",
  };
  assert.equal(formatJob(job),[
    "🚨 *BRILLIO HIRING*",
    "",
    "💼 Role: Associate Engineer, Applications & Platforms",
    "📍 Location: Chennai, Tamil Nadu, India",
    "🎓 Experience: Entry level; up to 2 years",
    "💻 Category: IT",
    "",
    "🔗 Apply Link: https://hdcareers.in/jobs/brillio-associate-engineer-applications-platforms.html",
    "",
    "💚 WhatsApp: https://whatsapp.com/channel/0029VbAxOna7NoZvhuKX362z",
    "✈️ Telegram: https://t.me/HD_Careers",
  ].join("\n"));
});

test("preview only uses disclosed field classification and validates link",()=>{
  const base={company:"OtherCo",role:"Assistant",loc:"Hyderabad",
              expType:"fresher",expYears:"N/A",field:"nonit",
              page:"jobs/otherco-assistant.html"};
  const msg=formatJob(base);
  assert.match(msg,/Category: Non-IT/);
  assert.match(msg,/Experience: Freshers eligible/);
  assert.doesNotMatch(msg,/Qualification:|Package:|Application status can change/);
  assert.match(formatJob({...base,field:"",cat:"apprenticeship"}),/Category: Apprenticeship/);
  assert.match(formatJob({...base,field:"",cat:"unknown"}),/Category: Not specified/);
  assert.throws(()=>formatJob({...base,page:"../private"}),/Invalid published job URL/);
});
