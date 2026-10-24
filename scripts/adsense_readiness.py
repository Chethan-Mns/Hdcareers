#!/usr/bin/env python3
"""Source-backed AdSense readiness changes and static, JS-independent fallbacks."""
from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
JOBS = ROOT / "data" / "jobs.json"

# Internal records explicitly describe student/graduate/intern roles with no
# substantiated experienced-only requirement. Preserve other ambiguous cases.
STUDENT_IDS = {231, 235, 237, 239, 221, 224, 209, 199, 201, 204, 205, 206, 207, 208, 191, 196, 173}
UNSPECIFIED_IDS = {232, 233, 236, 227, 212, 203}
OVERRIDES = {
    183: {
        "expType": "fresher",
        "expYears": "Final-year 2027 students; previous internships preferred, not required",
        "elig": "Final-year (2027) B.Tech/B.E./Dual Degree students from IIT, NIT or IIIT in CSE, IT or closely related CS branches. Strong academics and coding ability required. Prior internships, open-source work and projects are preferred.",
        "desc": "Merkle Science is hiring a Backend Software Engineer Intern in Bengaluru for a one-year hybrid internship. Work on Python Django/FastAPI backend services and REST APIs, PostgreSQL schemas and queries, Redis caching, tests, troubleshooting and performance improvements. The official posting specifies final-year 2027 IIT/NIT/IIIT engineering students in computer science-related branches; high performers may be considered for full-time roles subject to employer conditions.",
        "resp": ["Build and maintain Python backend services and REST APIs with Django/FastAPI.", "Design PostgreSQL models and optimize SQL queries.", "Use Redis for caching and service performance.", "Write tests, review code and troubleshoot production services.", "Collaborate with frontend and QA teams on integrated features."],
        "skills": ["Python", "Django", "FastAPI", "PostgreSQL", "Redis", "REST APIs", "Git", "DSA"],
        "workMode": "Hybrid",
        "batch": "2027",
        "sourceVerificationMethod": "Official Merkle Science Lever job page reviewed on 24 Oct 2026; eligibility and duties transcribed from employer listing."
    },
    109: {
        "elig": "Bachelor's or master's degree (or equivalent) in computer science or a related field; 0–2 years of relevant experience. Proficiency in Go, Java, C/C++, Scala or Python. Public cloud experience is a plus.",
        "resp": ["Design, develop, test, deploy and maintain cloud data-protection software.", "Build software for distributed systems and public-cloud environments.", "Manage engineering priorities, deadlines and deliverables."],
        "skills": ["Distributed systems", "Go", "Java", "C++", "Python", "AWS", "Azure", "GCP"],
        "sourceVerificationMethod": "Rubrik official Cloud: Azure careers posting reviewed on 24 Oct 2026."
    },
    101: {
        "elig": "Pursuing a Computer Science or Engineering degree at a Tier 1 college; at least one prior relevant engineering or backend/AI internship is required. Must work onsite in Bengaluru. Programming and problem-solving foundations expected.",
        "resp": ["Build scalable backend components on AWS serverless infrastructure.", "Participate in system design and implementation decisions.", "Develop proof-of-concepts for backend and AI feature integrations.", "Deliver production features with support from senior engineers."],
        "skills": ["AWS", "Serverless", "Backend engineering", "Distributed systems", "AI integration", "Debugging"],
        "sourceVerificationMethod": "Enterpret official Greenhouse posting reviewed on 24 Oct 2026."
    },
    89: {
        "elig": "Graduate applicant for ION Group India's 2027 Leadership Development Program. The employer listing specifies software engineering foundations, analytical problem solving, communication and teamwork; no exact degree/grade threshold is given in the accessible posting.",
        "desc": "ION Group's 2027 Leadership Development Program recruits Software Developers for Noida, Mumbai and Pune. Developers work with an Agile team on business analysis, software architecture, implementation, integration and automation for financial-market technology used by international clients. Confirm location preferences and any degree criteria with ION before applying.",
        "resp": ["Interpret business requirements and propose effective software solutions.", "Design, develop and integrate scalable, maintainable applications.", "Collaborate in Agile teams through the product delivery lifecycle.", "Build automation and resolve engineering and business problems."],
        "skills": ["Software development", "Agile", "Design patterns", "Software architecture", "Automation", "Problem solving"],
        "sourceVerificationMethod": "Official ION Group Lever 2027 Leadership Development Program listing reviewed on 24 Oct 2026."
    },
    88: {
        "elig": "2026 BE/B.Tech graduates in CS, IT, Electronics, AI/ML, Data Science or related branches. Minimum 80% (or equivalent CGPA) in 10th, 12th and graduation, with no current or past backlogs. Strong DSA, OOP, DBMS, OS, networking and Java foundations required.",
        "desc": "Zycus seeks 2026 engineering graduates for Software Engineer roles in Mumbai. The work includes Java/Spring Boot backend engineering, REST APIs, microservices and AI-assisted enterprise software development. The employer lists an 80% academic requirement in 10th, 12th and engineering, and no history of backlogs or arrears.",
        "resp": ["Develop Java/Spring Boot backend services, REST APIs and microservices.", "Work with data models, databases and application integrations.", "Write tested, maintainable code and participate in code reviews.", "Use AI coding tools to learn, debug and contribute to enterprise engineering."],
        "skills": ["Java", "Spring Boot", "REST APIs", "SQL", "OOP", "DSA", "Git", "AI tools"],
        "batch": "2026",
        "sourceVerificationMethod": "Zycus official 2026 Graduate Software Engineer posting reviewed on 24 Oct 2026."
    },
    108: {
        "elig": "This is explicitly titled 'New Grad – Software Engineer (Evergreen PPO)' by Visa and located in Bengaluru. Detailed degree, batch and experience thresholds could not be verified from the JavaScript-only application page; review them with Visa before applying."
    },
    105: {
        "elig": "Microsoft Software Engineer II role. The existing HD Careers record lists 4+ years of experience, but the detailed official requirements are not independently accessible; confirm degree, technical requirements and experience on the Microsoft application page."
    },
    176: {
        "elig": "AiPrise Software Engineer I in Bengaluru, working on APIs, compliance orchestration, case management and AI-agent integrations. The official application page requires JavaScript, so precise education and experience thresholds remain unverified; check the employer's criteria before applying."
    },
    240: {
        "elig": "Barclays Software Engineer role. The exact official listing was manually confirmed active, but its degree, graduation batch and years-of-experience requirements could not be independently retrieved. The 'fresher' designation is not yet substantiated; verify eligibility directly with Barclays.",
        "expType": "not-specified",
        "expYears": "Not independently confirmed",
        "resp": ["Software engineering responsibilities and technology requirements must be checked on the exact Barclays employer listing."],
        "desc": "Barclays has an official Software Engineer opening with a manually verified application link. HD Careers has not independently confirmed its degree, years-of-experience or technology requirements, so this opportunity is listed with eligibility unverified rather than advertised as guaranteed fresher hiring."
    }
}

def apply_job_patches() -> dict:
    jobs = json.loads(JOBS.read_text(encoding="utf-8"))
    changed, ids = 0, []
    for job in jobs:
        if job.get("status") != "active":
            continue
        id_ = job.get("id")
        updates = {}
        if id_ in STUDENT_IDS and job.get("expType") == "experienced":
            updates["expType"] = "fresher"
        if id_ in UNSPECIFIED_IDS and job.get("expType") == "experienced":
            updates["expType"] = "not-specified"
        updates.update(OVERRIDES.get(id_, {}))
        if updates and any(job.get(k) != v for k, v in updates.items()):
            job.update(updates)
            changed += 1
            ids.append(id_)
    if changed:
        JOBS.write_text(json.dumps(jobs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"updated": changed, "ids": ids}

def sub_id(s: str, id_: str, value: object) -> str:
    pattern = r'(<(?:strong|b)[^>]*\bid="' + re.escape(id_) + r'"[^>]*>).*?(</(?:strong|b)>)'
    return re.sub(pattern, lambda m: m[1] + html.escape(str(value)) + m[2], s, count=1, flags=re.S)

def sub_attr(s: str, attr: str, value: object) -> str:
    pattern = r'(<(?:span|strong)[^>]*\b' + re.escape(attr) + r'(?:="[^"]*")?[^>]*>).*?(</(?:span|strong)>)'
    return re.sub(pattern, lambda m: m[1] + html.escape(str(value)) + m[2], s, flags=re.S)

def write(path: Path, content: str, dry_run: bool) -> int:
    before = path.read_text(encoding="utf-8")
    if before == content:
        return 0
    if not dry_run:
        path.write_text(content, encoding="utf-8")
    return 1

def pre_render_site(jobs: list[dict], dry_run: bool = False) -> int:
    active = [j for j in jobs if j.get("status") == "active"]
    companies = Counter(str(j.get("company") or "").strip() for j in active if j.get("company"))
    skills = Counter(str(v).strip() for j in active for v in j.get("skills", []) if str(v).strip())
    from generate import build_public_insights
    insights = build_public_insights(jobs)
    pins = insights["cityPins"]
    total_mapped = sum(p["count"] for p in pins)
    top = pins[0] if pins else {"city": "None", "count": 0}
    next_cities = ", ".join(p["city"] for p in pins[1:3]) or "other locations"
    safe = lambda s: html.escape(str(s), quote=True)
    targets = 0

    index_path = ROOT / "index.html"
    home = index_path.read_text(encoding="utf-8")
    home = sub_id(home, "hdpJobs", len(active))
    home = sub_id(home, "hdpEmployers", len(companies))
    home = sub_attr(home, "data-hdm-total", total_mapped)
    home = sub_attr(home, "data-hdm-cities", len(pins))
    home = sub_attr(home, "data-hdm-leader", top["city"])
    home = sub_attr(home, "data-hdm-leader-count", top["count"])
    home = sub_attr(home, "data-hdm-share", str(round(top["count"] * 100 / total_mapped)) + "%" if total_mapped else "0%")
    home = sub_attr(home, "data-hdm-runnerup", next_cities)
    featured = []
    for name in ("Deloitte", "EY", "Amazon", "Accenture"):
        listings = [j for j in active if j.get("company", "").casefold() == name.casefold()]
        if listings:
            featured.append('<a class="hdp-company" href="' + safe(listings[0]["page"]) + '"><h3>' + safe(name) +
                            '</h3><span class="hdp-count">' + str(len(listings)) + ' active listings →</span></a>')
    home = re.sub(r'(<div id="hdpCompanies" class="hdp-companies">).*?(</div>)',
                  lambda m: m[1] + "".join(featured) + m[2], home, count=1, flags=re.S)
    last = sorted(active, key=lambda j: str(j.get("publishedAt") or ""), reverse=True)[:4]
    recent = ''.join('<article class="hdp-featured-item"><div class="hdp-job-company">' + safe(j.get("company", "")) +
       '</div><h3>' + safe(j.get("role", "")) + '</h3><p>' + safe(j.get("loc", "")) +
       '</p><a class="hdp-apply" href="' + safe(j.get("page", "")) + '">View &amp; Apply →</a></article>' for j in last)
    home = re.sub(r'(<div id="hdpRecent" class="hdp-featured">).*?(</div>)', lambda m: m[1] + recent + m[2],
                  home, count=1, flags=re.S)
    bars = ', '.join('<a href="index.html#resultsSection">' + safe(p["city"]) +
                     ' (' + str(p["count"]) + ')</a>' for p in pins[:6])
    home = home.replace('<p class="hdm-fineprint">Loading current city counts…</p>',
                        '<p class="hdm-fineprint">Current city listings: ' + bars + '</p>')
    home = home.replace("Only Deloitte, EY, Amazon and Accenture — with Active openings.",
                        "Current active opportunities from selected employers.")
    targets += write(index_path, home, dry_run)

    internships = sum(j.get("cat") == "internship" or "intern" in str(j.get("role", "")).casefold() for j in active)
    software = sum(j.get("cat") == "it" for j in active)
    kpis = {"hiArtActive": len(active), "hiArtCompanies": len(companies),
            "hiActive": len(active), "hiEmployers": len(companies),
            "hiFreshers": sum(j.get("expType") == "fresher" for j in active),
            "hiIT": software, "hiInternships": internships, "hiRingTotal": len(active)}
    for path in (ROOT / "insights.html", ROOT / "insights" / "weekly-hiring-insights.html"):
        s = path.read_text(encoding="utf-8")
        for id_, value in kpis.items():
            s = sub_id(s, id_, value)
        for attr, value in (("data-hdm-total", total_mapped), ("data-hdm-cities", len(pins))):
            s = sub_attr(s, attr, value)
        prefix = "../" if "weekly" in path.name else ""
        city_text = ''.join('<a href="' + prefix + 'index.html#resultsSection" class="hdm-fineprint">' +
                            safe(p["city"]) + ': ' + str(p["count"]) + ' listings</a> ' for p in pins[:6])
        s = s.replace('<p class="hdm-fineprint">Loading current city data…</p>', city_text)
        company_text = ''.join('<a href="' + prefix + 'index.html#resultsSection" class="hi-company">' +
                               safe(name) + ' — ' + str(count) + ' jobs</a> ' for name, count in companies.most_common(12))
        s = re.sub(r'(<div id="hiCompanies" class="hi-company-gallery">).*?(</div>)',
                   lambda m: m[1] + company_text + m[2], s, count=1, flags=re.S)
        skill_text = ''.join('<span class="hi-skill">' + safe(name) + ' (' + str(count) + ')</span> '
                             for name, count in skills.most_common(14))
        s = re.sub(r'(<div id="hiSkills" class="hi-skillwrap"[^>]*>).*?(</div>)',
                   lambda m: m[1] + skill_text + m[2], s, count=1, flags=re.S)
        targets += write(path, s, dry_run)
    return targets

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply-data", action="store_true")
    opts = parser.parse_args()
    if opts.apply_data:
        print(json.dumps(apply_job_patches()))

if __name__ == "__main__":
    main()
