from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "jobs.json"
INDEX_FILE = ROOT / "index.html"

REQUIRED = [
    "id", "page", "domain", "company", "salary", "logo", "role", "roleTag",
    "loc", "locationFilter", "batch", "elig", "cat", "expType", "expYears",
    "date", "desc", "resp", "apply", "status", "verifiedDate", "sourceName",
    "skills", "who", "workMode"
]

CAT_LABEL = {
    "it": "IT & Software",
    "internship": "Internship",
    "apprenticeship": "Apprenticeship",
    "campus": "Off-Campus",
    "remote": "Remote / WFH",
    "walkin": "Walk-in",
    "experienced": "Experienced",
    "govt": "Government Job",
}

CAT_BREADCRUMB = {
    "it": "IT / Software Jobs",
    "internship": "Internships",
    "apprenticeship": "Apprenticeships",
    "campus": "Off-Campus Jobs",
    "remote": "Remote / WFH Jobs",
    "walkin": "Walk-in Jobs",
    "experienced": "Experienced Jobs",
    "govt": "Government Jobs",
}

CAT_ICON = {
    "it": "fa-laptop-code",
    "internship": "fa-user-graduate",
    "apprenticeship": "fa-screwdriver-wrench",
    "campus": "fa-building",
    "remote": "fa-house-laptop",
    "walkin": "fa-people-arrows",
    "experienced": "fa-briefcase",
    "govt": "fa-landmark",
}

LOCAL_LOGOS = {
    "Infosys": "infosys.svg",
    "Zoho": "zoho.svg",
    "TCS": "tcs.svg",
    "Amazon": "amazon.svg",
    "Wipro": "wipro.svg",
    "Cognizant": "cognizant.svg",
    "Swiggy": "swiggy.svg",
    "HCLTech": "hcltech.svg",
    "Deloitte": "deloitte.svg",
    "ISRO": "isro.svg",
}

PAGE_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>$page_title</title>
<meta name="description" content="$meta_description">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="$canonical">
<meta property="og:type" content="article">
<meta property="og:title" content="$page_title">
<meta property="og:description" content="$meta_description">
<meta property="og:url" content="$canonical">
<link rel="icon" type="image/png" href="/assets/hd-careers-logo.png">
<link rel="apple-touch-icon" href="/assets/hd-careers-logo.png">
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/js/all.min.js" defer></script>
<style>
:root{--primary:#0b6fe8;--primary2:#0058c7;--dark:#071b35;--slate:#f4f7fb}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--slate);font-family:Inter,'Segoe UI',system-ui,-apple-system,sans-serif;color:var(--dark);-webkit-font-smoothing:antialiased}
a,button{transition:.18s ease}.card{transition:transform .18s ease,box-shadow .18s ease}.card:hover{transform:translateY(-2px);box-shadow:0 14px 30px rgba(7,27,53,.08)}
.hero{background:radial-gradient(circle at 90% 15%,rgba(40,145,255,.26),transparent 26%),linear-gradient(135deg,#071b35 0%,#0b3972 58%,#0b6fe8 100%)}
.reveal-on-scroll{opacity:0;transform:translateY(18px);transition:opacity .45s ease,transform .45s ease}.reveal-on-scroll.is-visible{opacity:1;transform:none}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}.reveal-on-scroll{opacity:1!important;transform:none!important;transition:none!important}}
</style>
</head>
<body>
<div class="bg-[var(--primary)] text-white text-xs sm:text-sm"><div class="max-w-6xl mx-auto px-4 py-2 flex items-center justify-center gap-2 text-center"><span class="bg-white/20 font-bold px-2 py-0.5 rounded text-[10px]">HD</span><span>Fresh job updates with official application sources</span><a href="https://t.me/HD_Careers" target="_blank" rel="noopener" class="font-bold underline">Join Telegram</a></div></div>
<header class="sticky top-0 z-40 bg-white/95 backdrop-blur border-b border-slate-200">
<div class="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between gap-4">
<a href="../index.html" class="flex items-center gap-3 min-w-0"><img src="../assets/hd-careers-logo.png" alt="HD Careers logo" class="w-11 h-11 object-contain rounded-xl bg-white border border-slate-100 p-1"><div><p class="font-black leading-none text-lg">HD Careers</p><p class="text-[10px] text-slate-500 mt-1">Jobs • Internships • Career updates</p></div></a>
<nav class="hidden md:flex items-center gap-5 text-sm font-semibold text-slate-600"><a href="../index.html">Home</a><a href="../index.html#jobs">Latest Jobs</a><a href="../about.html">About</a><a href="../contact.html">Contact</a></nav>
<div class="flex items-center gap-2"><a href="https://instagram.com/hd_careers" target="_blank" rel="noopener" class="w-10 h-10 rounded-xl bg-pink-50 text-pink-600 flex items-center justify-center" aria-label="Instagram"><i class="fa-brands fa-instagram"></i></a><a href="https://t.me/HD_Careers" target="_blank" rel="noopener" class="w-10 h-10 rounded-xl bg-sky-50 text-sky-600 flex items-center justify-center" aria-label="Telegram"><i class="fa-brands fa-telegram"></i></a></div>
</div>
</header>
<main>
<section class="hero text-white">
<div class="max-w-6xl mx-auto px-4 py-9 sm:py-12">
<div class="text-xs text-blue-100 flex flex-wrap items-center gap-2 mb-5"><a href="../index.html">Home</a><i class="fa-solid fa-chevron-right text-[9px]"></i><a href="../index.html#jobs">$breadcrumb</a><i class="fa-solid fa-chevron-right text-[9px]"></i><span class="text-white">$breadcrumb_job</span></div>
<div class="bg-white/10 border border-white/15 rounded-[28px] p-5 sm:p-7 backdrop-blur-sm">
<div class="flex flex-col lg:flex-row lg:items-center gap-5">
<div class="w-20 h-20 rounded-2xl bg-white flex items-center justify-center shrink-0 shadow-lg overflow-hidden"><img src="$favicon_url" alt="$company logo" class="w-[72%] h-[72%] object-contain" $logo_onerror></div>
<div class="flex-1 min-w-0"><div class="flex flex-wrap gap-2 mb-3"><span class="bg-blue-400/20 border border-blue-200/20 px-3 py-1 rounded-full text-xs font-bold"><i class="fa-solid $cat_icon mr-1"></i> $cat_label</span><span class="bg-emerald-400/20 border border-emerald-200/20 px-3 py-1 rounded-full text-xs font-bold">$candidate</span>$status_badge</div><h1 class="text-2xl sm:text-4xl font-black tracking-tight">$heading</h1><p class="text-blue-100 mt-2">$loc • $work_mode</p><p class="text-blue-200 text-xs mt-2">Posted $date • Last verified $verified_date</p></div>
<div class="flex lg:flex-col items-stretch gap-2 lg:w-48">$hero_action<button onclick="shareJob()" class="h-12 lg:h-11 px-4 rounded-xl border border-white/20 bg-white/10 hover:bg-white/15 font-bold"><i class="fa-solid fa-share-nodes mr-1.5"></i> Share</button></div>
</div></div></div>
</section>
<section class="max-w-6xl mx-auto px-4 py-7 sm:py-9 grid lg:grid-cols-[1fr_320px] gap-6 items-start">
<div class="space-y-5">
$status_notice
<div class="card bg-white border border-slate-200 rounded-2xl p-5 sm:p-6"><h2 class="text-xl font-black">Job Overview</h2><p class="text-slate-600 leading-relaxed mt-3">$desc</p><div class="grid sm:grid-cols-2 gap-3 mt-5"><div class="bg-slate-50 rounded-xl p-4"><p class="text-xs text-slate-500">Company</p><p class="font-bold mt-1">$company</p></div><div class="bg-slate-50 rounded-xl p-4"><p class="text-xs text-slate-500">Role</p><p class="font-bold mt-1">$role_tag</p></div><div class="bg-slate-50 rounded-xl p-4"><p class="text-xs text-slate-500">Location</p><p class="font-bold mt-1">$loc</p></div><div class="bg-slate-50 rounded-xl p-4"><p class="text-xs text-slate-500">Experience</p><p class="font-bold mt-1">$candidate / $exp_years</p></div><div class="bg-slate-50 rounded-xl p-4"><p class="text-xs text-slate-500">Qualification / Batch</p><p class="font-bold mt-1">$batch</p></div><div class="bg-slate-50 rounded-xl p-4"><p class="text-xs text-slate-500">Salary / Stipend</p><p class="font-bold mt-1">$salary</p></div></div></div>
<div class="card bg-white border border-slate-200 rounded-2xl p-5 sm:p-6"><h2 class="text-xl font-black"><i class="fa-solid fa-circle-check text-[var(--primary)] mr-2"></i>Eligibility</h2><p class="mt-4 text-slate-600 leading-relaxed">$elig</p></div>
<div class="card bg-white border border-slate-200 rounded-2xl p-5 sm:p-6"><h2 class="text-xl font-black"><i class="fa-solid fa-screwdriver-wrench text-[var(--primary)] mr-2"></i>Skills Mentioned</h2><div class="flex flex-wrap gap-2 mt-4">$skills</div></div>
<div class="card bg-white border border-slate-200 rounded-2xl p-5 sm:p-6"><h2 class="text-xl font-black"><i class="fa-solid fa-list-check text-[var(--primary)] mr-2"></i>Key Responsibilities</h2><ul class="mt-4 space-y-3 text-slate-600">$responsibilities</ul></div>
<div class="card bg-white border border-slate-200 rounded-2xl p-5 sm:p-6"><h2 class="text-xl font-black"><i class="fa-solid fa-user-check text-[var(--primary)] mr-2"></i>Who Should Apply?</h2><p class="mt-4 text-slate-600 leading-relaxed">$who</p></div>
$apply_section
<div class="card bg-white border border-slate-200 rounded-2xl p-5 sm:p-6"><h2 class="text-xl font-black"><i class="fa-solid fa-shield-halved text-[var(--primary)] mr-2"></i>Source & Verification</h2><p class="mt-3 text-slate-600">Source: <strong>$source_name</strong></p><p class="mt-1 text-slate-600">Last checked by HD Careers: <strong>$verified_date</strong></p><a href="$apply" target="_blank" rel="noopener nofollow" class="mt-4 inline-flex items-center text-[var(--primary)] font-bold">Open official source <i class="fa-solid fa-arrow-up-right-from-square ml-2 text-xs"></i></a><p class="mt-3 text-xs text-slate-500">Job information can change after publication. The employer's official page is the final source for eligibility, deadlines and application availability.</p></div>
$related_jobs
<div class="rounded-2xl bg-amber-50 border border-amber-200 p-5 text-sm text-amber-900"><p class="font-extrabold"><i class="fa-solid fa-triangle-exclamation mr-1"></i> Important</p><p class="mt-1 leading-relaxed">HD Careers is an independent job information platform. We do not charge candidates for applications and we are not the employer or recruitment agency for the jobs listed here.</p></div>
</div>
<aside class="space-y-5 lg:sticky lg:top-24">
<div class="card bg-white border border-slate-200 rounded-2xl p-5"><div class="flex items-center gap-3"><div class="w-14 h-14 rounded-xl border border-slate-200 bg-white flex items-center justify-center overflow-hidden"><img src="$favicon_url" alt="$company logo" class="w-[72%] h-[72%] object-contain" $logo_onerror></div><div><h3 class="font-black text-lg">Job Summary</h3><p class="text-xs text-slate-500">$company</p></div></div><div class="mt-4 divide-y divide-slate-100 text-sm"><div class="py-3 flex justify-between gap-4"><span class="text-slate-500">Status</span><span class="font-bold text-right">$status_label</span></div><div class="py-3 flex justify-between gap-4"><span class="text-slate-500">Category</span><span class="font-bold text-right">$cat_label</span></div><div class="py-3 flex justify-between gap-4"><span class="text-slate-500">Experience</span><span class="font-bold text-right">$exp_years</span></div><div class="py-3 flex justify-between gap-4"><span class="text-slate-500">Work mode</span><span class="font-bold text-right">$work_mode</span></div><div class="py-3 flex justify-between gap-4"><span class="text-slate-500">Verified</span><span class="font-bold text-right">$verified_date</span></div></div>$sidebar_action</div>
<div class="rounded-2xl p-5 text-white" style="background:linear-gradient(135deg,#0f9d58,#128c4c)"><h3 class="font-black text-lg">Get the next job first</h3><p class="text-sm text-green-50 mt-1">Join HD Careers for fresh job alerts.</p><a href="https://whatsapp.com/channel/0029VbAxOna7NoZvhuKX362z" target="_blank" rel="noopener" class="mt-4 block text-center bg-white text-green-700 font-bold py-2.5 rounded-xl">Join WhatsApp</a></div>
<div class="card bg-white border border-slate-200 rounded-2xl p-5"><h3 class="font-black">Need a correction?</h3><p class="text-sm text-slate-500 mt-2">Report an expired or inaccurate listing.</p><a href="../contact.html" class="text-sm text-[var(--primary)] font-semibold mt-3 block">Contact HD Careers</a></div>
</aside>
</section>
</main>
<footer class="bg-[var(--dark)] text-slate-300 mt-4"><div class="max-w-6xl mx-auto px-4 py-8"><div class="flex flex-col lg:flex-row justify-between gap-6"><div><p class="text-white font-black">HD Careers</p><p class="text-slate-400 text-xs mt-1 max-w-md">Independent job information platform helping candidates find and verify opportunities from official employer sources.</p></div><div class="flex flex-wrap gap-x-5 gap-y-2 text-sm"><a href="../about.html" class="hover:text-white">About</a><a href="../contact.html" class="hover:text-white">Contact</a><a href="../privacy-policy.html" class="hover:text-white">Privacy Policy</a><a href="../terms.html" class="hover:text-white">Terms</a><a href="../disclaimer.html" class="hover:text-white">Disclaimer</a></div></div><p class="text-xs text-slate-500 mt-6">&copy; 2026 HD Careers. All rights reserved.</p></div></footer>
<div id="toast" class="hidden fixed bottom-5 left-1/2 -translate-x-1/2 bg-slate-900 text-white text-sm font-semibold px-4 py-2.5 rounded-full shadow-2xl z-50"></div>
<script>
const revealObserver=('IntersectionObserver' in window)?new IntersectionObserver((entries)=>{entries.forEach(entry=>{if(entry.isIntersecting){entry.target.classList.add('is-visible');revealObserver.unobserve(entry.target)}})},{threshold:.12}):null;
document.querySelectorAll('.card, aside > div').forEach(el=>{el.classList.add('reveal-on-scroll');if(revealObserver)revealObserver.observe(el);else el.classList.add('is-visible')});
async function shareJob(){const url=window.location.href;const title=$share_title;const text=$share_text+"\\nView job: "+url;try{if(navigator.share){await navigator.share({title,text,url})}else{await navigator.clipboard.writeText(text);showToast('Job link copied')}}catch(e){}}
function showToast(msg){const t=document.getElementById('toast');t.textContent=msg;t.classList.remove('hidden');clearTimeout(window.__toast);window.__toast=setTimeout(()=>t.classList.add('hidden'),1700)}
</script>
</body>
</html>
""")


def load_jobs() -> list[dict]:
    if not DATA_FILE.exists():
        raise SystemExit(f"Missing {DATA_FILE.relative_to(ROOT)}")

    try:
        jobs = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {DATA_FILE.relative_to(ROOT)}: {exc}") from exc

    if not isinstance(jobs, list) or not jobs:
        raise SystemExit("data/jobs.json must contain a non-empty JSON array")

    seen_ids = set()
    seen_pages = set()

    for pos, job in enumerate(jobs, start=1):
        if not isinstance(job, dict):
            raise SystemExit(f"Job #{pos} must be an object")

        missing = [key for key in REQUIRED if key not in job]
        if missing:
            raise SystemExit(f"Job #{pos} is missing: {', '.join(missing)}")

        if job["id"] in seen_ids:
            raise SystemExit(f"Duplicate job id: {job['id']}")
        seen_ids.add(job["id"])

        page = str(job["page"])
        if page in seen_pages:
            raise SystemExit(f"Duplicate job page: {page}")
        seen_pages.add(page)

        if not page.startswith("jobs/") or not page.endswith(".html") or ".." in Path(page).parts:
            raise SystemExit(f"Invalid job page path: {page}")

        if job["cat"] not in CAT_LABEL:
            raise SystemExit(f"Unsupported category '{job['cat']}' for job id {job['id']}")

        if job["expType"] not in {"fresher", "experienced"}:
            raise SystemExit(f"Unsupported expType '{job['expType']}' for job id {job['id']}")

        if job["status"] not in {"active", "expired"}:
            raise SystemExit(f"Unsupported status '{job['status']}' for job id {job['id']}")

        if not isinstance(job["resp"], list) or not job["resp"]:
            raise SystemExit(f"Job id {job['id']} must have at least one responsibility")

        if not isinstance(job["skills"], list) or not job["skills"]:
            raise SystemExit(f"Job id {job['id']} must have at least one skill")

        if not str(job["who"]).strip() or not str(job["sourceName"]).strip() or not str(job["verifiedDate"]).strip():
            raise SystemExit(f"Job id {job['id']} requires who, sourceName and verifiedDate")

        if not isinstance(job["logo"], list) or len(job["logo"]) != 2:
            raise SystemExit(f"Job id {job['id']} logo must be [initials, color]")

    return jobs


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def render_responsibilities(items: list[str]) -> str:
    rows = []
    for index, item in enumerate(items, start=1):
        rows.append(
            '<li class="flex gap-3">'
            f'<span class="w-6 h-6 rounded-full bg-blue-50 text-[var(--primary)] text-xs font-bold flex items-center justify-center shrink-0">{index}</span>'
            f'<span>{esc(item)}</span>'
            '</li>'
        )
    return "".join(rows)


def render_skills(items: list[str]) -> str:
    return "".join(
        f'<span class="px-3 py-1.5 rounded-full bg-blue-50 border border-blue-100 text-sm font-semibold text-blue-800">{esc(item)}</span>'
        for item in items
    )


def logo_onerror(company: str) -> str:
    filename = LOCAL_LOGOS.get(company)
    if filename:
        return (
            "onerror=\"this.onerror=null;"
            f"this.src='../assets/logos/{esc(filename)}';"
            "this.className='w-[90%] h-[90%] object-contain'\""
        )
    return "onerror=\"this.style.display='none'\""


def render_related_jobs(job: dict, jobs: list[dict]) -> str:
    active = [j for j in jobs if j["id"] != job["id"] and j.get("status") == "active"]
    ranked = sorted(
        active,
        key=lambda j: (
            0 if j.get("cat") == job.get("cat") else 1,
            0 if j.get("expType") == job.get("expType") else 1,
            -int(j.get("id", 0)),
        ),
    )[:4]
    if not ranked:
        return ""
    cards = []
    for other in ranked:
        href = Path(str(other["page"])).name
        cards.append(
            '<a class="block rounded-xl border border-slate-200 p-4 hover:border-blue-300 hover:bg-blue-50/40" '
            f'href="{esc(href)}"><p class="font-black">{esc(other["company"])}</p>'
            f'<p class="text-sm text-slate-600 mt-1">{esc(other["role"])}</p>'
            f'<p class="text-xs text-slate-400 mt-2">{esc(other["loc"])}</p></a>'
        )
    return (
        '<div class="card bg-white border border-slate-200 rounded-2xl p-5 sm:p-6">'
        '<h2 class="text-xl font-black"><i class="fa-solid fa-link text-[var(--primary)] mr-2"></i>Related Jobs</h2>'
        '<div class="grid sm:grid-cols-2 gap-3 mt-4">' + "".join(cards) + '</div></div>'
    )


def render_job_page(job: dict, jobs: list[dict]) -> str:
    company = str(job["company"])
    role = str(job["role"])
    heading = f"{company} {role}"
    page_title = f"{heading} | HD Careers"
    candidate = "Fresher / Entry-level" if job["expType"] == "fresher" else "Experienced"
    cat = str(job["cat"])
    status = str(job.get("status", "active"))
    status_label = "Active" if status == "active" else "Expired / Closed"
    favicon_url = f"https://www.google.com/s2/favicons?domain={esc(job['domain'])}&sz=128"
    canonical = f"https://hdcareers.in/{str(job['page']).lstrip('/')}"
    meta_description = f"{heading} - verified job details, eligibility, skills, location and official source on HD Careers."
    share_text = f"{company} - {role}\\n{job['loc']}"

    if status == "active":
        status_badge = '<span class="bg-green-400/20 border border-green-200/20 px-3 py-1 rounded-full text-xs font-bold"><i class="fa-solid fa-circle-check mr-1"></i> Active</span>'
        hero_action = f'<a href="{esc(job["apply"])}" target="_blank" rel="noopener nofollow" class="flex-1 text-center bg-white text-[var(--primary)] font-extrabold px-5 py-3 rounded-xl hover:bg-blue-50">Official Apply <i class="fa-solid fa-arrow-up-right-from-square ml-1"></i></a>'
        status_notice = f'<div class="rounded-2xl bg-emerald-50 border border-emerald-200 p-4 text-sm text-emerald-900"><strong>Verified active:</strong> HD Careers checked the official source on {esc(job["verifiedDate"])}. Availability can still change, so confirm once more before submitting.</div>'
        apply_section = (
            '<div class="card bg-white border border-slate-200 rounded-2xl p-5 sm:p-6"><h2 class="text-xl font-black"><i class="fa-solid fa-route text-[var(--primary)] mr-2"></i>How to Apply</h2>'
            f'<div class="mt-4 space-y-3 text-slate-600"><p>1. Open the official {esc(company)} application page using the button below.</p><p>2. Re-check the current eligibility, location and any deadline on the employer site.</p><p>3. Complete the application only on the official employer or authorized recruitment portal.</p></div>'
            f'<a href="{esc(job["apply"])}" target="_blank" rel="noopener nofollow" class="mt-5 inline-flex items-center justify-center bg-green-500 hover:bg-green-600 text-white font-extrabold px-6 py-3 rounded-xl">Continue to Official Website <i class="fa-solid fa-arrow-up-right-from-square ml-2"></i></a></div>'
        )
        sidebar_action = f'<a href="{esc(job["apply"])}" target="_blank" rel="noopener nofollow" class="mt-4 block text-center bg-[var(--primary)] hover:bg-[var(--primary2)] text-white font-extrabold py-3 rounded-xl">Apply on Official Site</a>'
    else:
        status_badge = '<span class="bg-red-400/20 border border-red-200/20 px-3 py-1 rounded-full text-xs font-bold"><i class="fa-solid fa-circle-xmark mr-1"></i> Expired</span>'
        hero_action = '<span class="flex-1 text-center bg-white/20 text-white font-extrabold px-5 py-3 rounded-xl cursor-not-allowed">Application Closed</span>'
        status_notice = f'<div class="rounded-2xl bg-red-50 border border-red-200 p-4 text-sm text-red-900"><strong>Application status:</strong> This listing was marked expired or closed when last checked on {esc(job["verifiedDate"])}. The page remains available for reference; use Latest Jobs for current openings.</div>'
        apply_section = '<div class="card bg-white border border-slate-200 rounded-2xl p-5 sm:p-6"><h2 class="text-xl font-black">Application Closed</h2><p class="mt-3 text-slate-600">This job is no longer treated as an active opening on HD Careers. Browse current jobs instead of relying on an old application link.</p><a href="../index.html#jobs" class="mt-5 inline-flex bg-[var(--primary)] text-white font-bold px-5 py-3 rounded-xl">Browse Latest Jobs</a></div>'
        sidebar_action = '<a href="../index.html#jobs" class="mt-4 block text-center bg-slate-900 text-white font-extrabold py-3 rounded-xl">Browse Active Jobs</a>'

    values = {
        "page_title": esc(page_title),
        "meta_description": esc(meta_description),
        "canonical": esc(canonical),
        "breadcrumb": esc(CAT_BREADCRUMB[cat]),
        "breadcrumb_job": esc(f"{company} {job['roleTag']}"),
        "favicon_url": favicon_url,
        "company": esc(company),
        "logo_onerror": logo_onerror(company),
        "cat_icon": CAT_ICON[cat],
        "cat_label": esc(CAT_LABEL[cat]),
        "candidate": candidate,
        "status_badge": status_badge,
        "status_label": status_label,
        "salary": esc(job["salary"]),
        "heading": esc(heading),
        "loc": esc(job["loc"]),
        "work_mode": esc(job["workMode"]),
        "batch": esc(job["batch"]),
        "date": esc(job["date"]),
        "verified_date": esc(job["verifiedDate"]),
        "apply": esc(job["apply"]),
        "desc": esc(job["desc"]),
        "role_tag": esc(job["roleTag"]),
        "exp_years": esc(job["expYears"]),
        "elig": esc(job["elig"]),
        "skills": render_skills(job["skills"]),
        "who": esc(job["who"]),
        "responsibilities": render_responsibilities(job["resp"]),
        "source_name": esc(job["sourceName"]),
        "hero_action": hero_action,
        "status_notice": status_notice,
        "apply_section": apply_section,
        "sidebar_action": sidebar_action,
        "related_jobs": render_related_jobs(job, jobs),
        "share_title": json.dumps(page_title, ensure_ascii=False),
        "share_text": json.dumps(share_text, ensure_ascii=False),
    }

    return PAGE_TEMPLATE.substitute(values)


def update_index(jobs: list[dict], dry_run: bool) -> bool:
    source = INDEX_FILE.read_text(encoding="utf-8")
    start_marker = "const JOBS = ["
    start = source.find(start_marker)
    if start == -1:
        raise SystemExit("Could not find 'const JOBS = [' in index.html")

    end = source.find("\n]\n\nconst CATS=", start)
    skip = 2
    if end == -1:
        end = source.find("\n];\n\nconst CATS=", start)
        skip = 3
    if end == -1:
        raise SystemExit("Could not find the end of the JOBS array in index.html")

    active_jobs = [job for job in jobs if job.get("status") == "active"]
    jobs_json = json.dumps(active_jobs, ensure_ascii=False, indent=2)
    replacement = "const JOBS = " + jobs_json
    updated = source[:start] + replacement + source[end + skip:]

    if updated == source:
        return False

    if not dry_run:
        INDEX_FILE.write_text(updated, encoding="utf-8")
    return True


def write_job_pages(jobs: list[dict], dry_run: bool) -> tuple[int, int, int]:
    created = 0
    changed = 0
    deleted = 0
    expected = {str(job["page"]) for job in jobs}

    jobs_dir = ROOT / "jobs"
    if jobs_dir.exists():
        for target in jobs_dir.glob("*.html"):
            rel = target.relative_to(ROOT).as_posix()
            if rel not in expected:
                deleted += 1
                if not dry_run:
                    target.unlink()

    for job in jobs:
        target = ROOT / job["page"]
        output = render_job_page(job, jobs)

        if not target.exists():
            created += 1
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(output, encoding="utf-8")
            continue

        current = target.read_text(encoding="utf-8")
        if current != output:
            changed += 1
            if not dry_run:
                target.write_text(output, encoding="utf-8")

    return created, changed, deleted


def write_support_files(jobs: list[dict], dry_run: bool) -> int:
    changed = 0
    urls = [
        "https://hdcareers.in/",
        "https://hdcareers.in/about.html",
        "https://hdcareers.in/contact.html",
        "https://hdcareers.in/privacy-policy.html",
        "https://hdcareers.in/terms.html",
        "https://hdcareers.in/disclaimer.html",
    ]
    urls.extend(f"https://hdcareers.in/{job['page']}" for job in jobs)
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(
        f"  <url><loc>{html.escape(url)}</loc></url>\n" for url in urls
    ) + "</urlset>\n"
    robots = "User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /api/\n\nSitemap: https://hdcareers.in/sitemap.xml\n"

    for path, content in [(ROOT / "sitemap.xml", sitemap), (ROOT / "robots.txt", robots)]:
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        if current != content:
            changed += 1
            if not dry_run:
                path.write_text(content, encoding="utf-8")
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate HD Careers homepage data, job pages, sitemap and robots files from data/jobs.json."
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing files.")
    args = parser.parse_args()

    jobs = load_jobs()
    index_changed = update_index(jobs, args.dry_run)
    created, changed, deleted = write_job_pages(jobs, args.dry_run)
    support_changed = write_support_files(jobs, args.dry_run)

    mode = "DRY RUN" if args.dry_run else "DONE"
    active = sum(1 for job in jobs if job.get("status") == "active")
    expired = len(jobs) - active
    print(f"[{mode}] {len(jobs)} jobs loaded ({active} active, {expired} expired)")
    print(f"index.html: {'would update' if args.dry_run and index_changed else 'updated' if index_changed else 'no change'}")
    print(f"job pages: {created} new, {changed} updated, {deleted} removed")
    print(f"support files: {support_changed} changed")

    if not args.dry_run:
        print("Run: python3 generate.py")


if __name__ == "__main__":
    main()
