import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {classifyJob,experienceLevel,jobField,isTrainingJob} from "../lib/job-classification.js";

const role=(name,years,skills=[],other={})=>({role:name,expYears:years,skills,...other});
test("Fresher accepts 0, 0-1, 0-2 and 0-3 years",()=>{
  for(const yrs of ["0 years","0–1 years","0-2 years","0 to 3 years","0+ years","0–1 years; freshers eligible"]){
    assert.equal(experienceLevel(role("Software Developer",yrs)), "fresher",yrs);
  }
});
test("Experienced excludes zero: 1-2, 2-4, 1+ and at least 2 years",()=>{
  for(const yrs of ["1–2 years","1-2 years","2–4 years","1+ years","At least 2 years experience","3 years"]){
    assert.equal(experienceLevel(role("Developer",yrs)), "experienced",yrs);
  }
});
test("Zero accepted for one degree path still means fresher",()=>{
  assert.equal(experienceLevel(role("AI Engineer","0 years with Master's; 2 years with Bachelor's")),"fresher");
});
test("Unknown experience is not silently called fresher",()=>{
  assert.equal(experienceLevel(role("Analyst","Not specified",[],{expType:"not-specified"})),"not-specified");
});
test("Technical roles are IT even when called analyst; support, sales and BPO take precedence",()=>{
  assert.equal(jobField(role("Data Analyst","0-1 years",["SQL","Python"],{field:"nonit"})),"it");
  assert.equal(jobField(role("Software Developer","1-2 years")),"it");
  assert.equal(jobField(role("BPO Executive","0-2 years",["SQL"])),"nonit");
  assert.equal(jobField(role("Sales Associate","0-2 years",["Python"])),"nonit");
  assert.equal(jobField(role("Customer Support Engineer","0-1 years",["Java"])),"nonit");
  assert.equal(jobField(role("Service Desk Analyst","0-1 years",["SQL"])),"nonit");
});
test("Internship and apprenticeship stay separate from full-time buckets",()=>{
  const intern=role("Backend Software Intern","Student internship",["Python"],{cat:"it",expType:"fresher"});
  assert.equal(isTrainingJob(intern),true);
  assert.equal(classifyJob(intern).cat,"internship");
  assert.equal(classifyJob({...intern,role:"CAD Design Apprenticeship"}).cat,"apprenticeship");
});
test("Homepage filter functions exclude all internships from full-time fresher IT",()=>{
  const html=fs.readFileSync(new URL("../index.html",import.meta.url),"utf8");
  const start=html.indexOf("function hdTraining(j){"),end=html.indexOf("function categoryCount(k){",start);
  assert.ok(start>=0&&end>start);
  const functions=html.slice(start,end);
  const {jobCategories,careerLabel}=new Function(functions+"; return {jobCategories,careerLabel};")();
  const intern=role("Software Engineer Intern","0–1 years",["Python"],{cat:"it",field:"it",expType:"fresher"});
  assert.equal(jobCategories(intern).includes("fresher-it"),false);
  assert.equal(jobCategories(intern).includes("internship"),true);
  assert.equal(careerLabel(intern),"Internship");
  const apprenticeship={...intern,role:"CAD Design Apprenticeship",cat:"apprenticeship"};
  assert.equal(jobCategories(apprenticeship).includes("apprenticeship"),true);
  assert.equal(jobCategories(apprenticeship).includes("fresher-it"),false);
  const fresh=role("Software Developer","0-2 years",["Python"],{cat:"it",field:"it",expType:"experienced"});
  assert.equal(jobCategories(fresh).includes("fresher-it"),true);
  assert.equal(jobCategories(fresh).includes("experienced-it"),false);
  const experienced=role("Customer Support Associate","1–2 years",["SQL"],{cat:"it",field:"it",expType:"fresher"});
  assert.equal(jobCategories(experienced).includes("experienced-nonit"),true);
  assert.equal(jobCategories(experienced).includes("fresher-nonit"),false);
});
