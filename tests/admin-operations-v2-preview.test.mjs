import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
const html=fs.readFileSync(new URL("../preview/admin-operations-v2.html",import.meta.url),"utf8");
const api=fs.readFileSync(new URL("../api/admin/operations-preview.js",import.meta.url),"utf8");
test("standalone HTML has syntactically valid interactive JavaScript",()=>{
 const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
 assert.equal(scripts.length,1,"Preview must be self-contained with one inline app script");
 assert.doesNotThrow(()=>new vm.Script(scripts[0][1],{filename:"admin-operations-v2.html"}));
});
test("native-sized preview has functional four-tab navigation and distinct live/demo modes",()=>{
 for(const v of ['today','publish','expiry','jobs'])assert.match(html,new RegExp("id:'"+v+"'"));
 for(const s of ['data-act="simulate"','data-act="conflict"','data-act="live"','data-act="demo"','data-act="simPublish"','data-act="refresh"'])assert.ok(html.includes(s),s);
 assert.match(html,/minimum 60 minutes/i);
 assert.match(html,/read-only/i);
});
test("live preview uses authenticated read-only telemetry not publishing actions",()=>{
 assert.match(api,/requireAdmin\(req,res,\["owner","job_editor"\]\)/);
 assert.match(api,/req.method!=="GET"/);
 assert.match(api,/VERCEL_ENV==="production"/);
 assert.match(api,/telegram-hourly-queue.json/);
 assert.match(api,/telegram-deliveries.json/);
 assert.match(api,/actions\/workflows\/admin-job-generator.yml/);
 assert.ok(!/method:\s*["'](?:POST|PUT|PATCH|DELETE)["']/.test(api));
 assert.ok(!/GITHUB_PUBLISH_TOKEN.*res\.status/.test(api));
});
test("demo simulated commit conflict never invokes actual publish endpoint",()=>{
 assert.match(html,/Simulate commit conflict/);
 assert.match(html,/re-read latest main and rebuild/);
 assert.match(html,/no real GitHub or Telegram requests/);
 assert.ok(!/fetch\(\s*['"]\/api\/admin\/publish['"]/.test(html));
 assert.ok(!/fetch\(\s*['"]\/api\/admin\/review['"]/.test(html));
});