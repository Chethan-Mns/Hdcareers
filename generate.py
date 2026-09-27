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
    "date", "desc", "resp", "apply"
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
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/js/all.min.js" defer></script>
<style>
:root{--primary:#0b6fe8;--primary2:#0058c7;--dark:#071b35;--slate:#f4f7fb;--white:#fff}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--slate);font-family:'Segoe UI',system-ui,-apple-system,sans-serif;color:var(--dark)}
a,button{transition:.18s ease}.card{transition:transform .18s ease,box-shadow .18s ease}.card:hover{transform:translateY(-2px);box-shadow:0 14px 30px rgba(7,27,53,.08)}
.hero{background:radial-gradient(circle at 90% 15%,rgba(40,145,255,.26),transparent 26%),linear-gradient(135deg,#071b35 0%,#0b3972 58%,#0b6fe8 100%)}
.reveal-on-scroll{opacity:0;transform:translateY(22px) scale(.99);transition:opacity .58s cubic-bezier(.22,1,.36,1),transform .58s cubic-bezier(.22,1,.36,1);transition-delay:var(--reveal-delay,0ms)}
.reveal-on-scroll.is-visible{opacity:1;transform:none}
button:active,a:active{transform:scale(.98)}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}.reveal-on-scroll{opacity:1!important;transform:none!important;transition:none!important}}
</style>
</head>
<body>
<div class="bg-[var(--primary)] text-white text-xs sm:text-sm">
<div class="max-w-6xl mx-auto px-4 py-2 flex items-center justify-center gap-2 text-center"><span class="bg-white/20 font-bold px-2 py-0.5 rounded text-[10px]">LIVE</span><span>Get daily job alerts from HD Careers</span><a href="https://whatsapp.com/channel/0029VamZKemKLaHrHF8Mwc3I" target="_blank" rel="noopener" class="font-bold underline">Join WhatsApp <i class="fa-brands fa-whatsapp"></i></a></div>
</div>
<header class="sticky top-0 z-40 bg-white/95 backdrop-blur border-b border-slate-200">
<div class="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between gap-4">
<a href="../index.html" class="flex items-center gap-3 min-w-0" aria-label="HD Careers home"><img src="../assets/hd-careers-logo.png" alt="HD Careers logo" class="w-11 h-11 object-contain rounded-xl bg-white border border-slate-100 p-1 shrink-0"><div class="min-w-0"><p class="font-black leading-none text-lg">HD Careers</p><p class="text-[10px] text-slate-500 mt-1">Jobs • Internships • Apprenticeships</p></div></a>
<nav class="hidden md:flex items-center gap-6 text-sm font-semibold text-slate-600"><a href="../index.html" class="hover:text-[var(--primary)]">Home</a><a href="../index.html#jobs" class="hover:text-[var(--primary)]">Jobs</a><a href="mailto:helpdeskinreallife@gmail.com" class="hover:text-[var(--primary)]">Contact Us</a></nav>
<div class="flex items-center gap-2"><a href="https://instagram.com/hd_careers" target="_blank" rel="noopener" class="w-10 h-10 rounded-xl bg-pink-50 text-pink-600 flex items-center justify-center" aria-label="Instagram"><i class="fa-brands fa-instagram"></i></a><a href="https://t.me/HD_Careers" target="_blank" rel="noopener" class="w-10 h-10 rounded-xl bg-sky-50 text-sky-600 flex items-center justify-center" aria-label="Telegram"><i class="fa-brands fa-telegram"></i></a></div>
</div>
</header>
<main>
<section class="hero text-white">
<div class="max-w-6xl mx-auto px-4 py-9 sm:py-12">
<div class="text-xs text-blue-100 flex flex-wrap items-center gap-2 mb-5"><a href="../index.html" class="hover:text-white">Home</a><i class="fa-solid fa-chevron-right text-[9px]"></i><a href="../index.html#jobs" class="hover:text-white">$breadcrumb</a><i class="fa-solid fa-chevron-right text-[9px]"></i><span class="text-white">$breadcrumb_job</span></div>
<div class="bg-white/10 border border-white/15 rounded-[28px] p-5 sm:p-7 backdrop-blur-sm">
<div class="flex flex-col lg:flex-row lg:items-center gap-5">
<div class="w-20 h-20 rounded-2xl bg-white flex items-center justify-center shrink-0 shadow-lg overflow-hidden"><img src="$favicon_url" alt="$company logo" class="w-[72%] h-[72%] object-contain" $logo_onerror></div>
<div class="flex-1 min-w-0"><div class="flex flex-wrap gap-2 mb-3"><span class="bg-blue-400/20 border border-blue-200/20 px-3 py-1 rounded-full text-xs font-bold"><i class="fa-solid $cat_icon mr-1"></i> $cat_label</span><span class="bg-emerald-400/20 border border-emerald-200/20 px-3 py-1 rounded-full text-xs font-bold">$candidate</span><span class="bg-white/10 border border-white/15 px-3 py-1 rounded-full text-xs font-bold">$salary</span></div><h1 class="text-2xl sm:text-4xl font-black tracking-tight">$heading</h1><p class="text-blue-100 mt-2">$loc • $batch • Posted $date</p></div>
<div class="flex lg:flex-col items-stretch gap-2 lg:w-44"><a href="$apply" target="_blank" rel="noopener" class="flex-1 text-center bg-white text-[var(--primary)] font-extrabold px-5 py-3 rounded-xl hover:bg-blue-50">Official Apply <i class="fa-solid fa-arrow-up-right-from-square ml-1"></i></a><button onclick="shareJob()" class="h-12 lg:h-11 px-4 rounded-xl border border-white/20 bg-white/10 hover:bg-white/15 font-bold"><i class="fa-solid fa-share-nodes mr-1.5"></i> Share</button></div>
</div></div></div>
</section>
<section class="max-w-6xl mx-auto px-4 py-7 sm:py-9 grid lg:grid-cols-[1fr_320px] gap-6 items-start">
<div class="space-y-5">
<div class="card bg-white border border-slate-200 rounded-2xl p-5 sm:p-6"><h2 class="text-xl font-black">Job Overview</h2><p class="text-slate-600 leading-relaxed mt-3">$desc</p><div class="grid sm:grid-cols-2 gap-3 mt-5"><div class="bg-slate-50 rounded-xl p-4"><p class="text-xs text-slate-500">Company</p><p class="font-bold mt-1">$company</p></div><div class="bg-slate-50 rounded-xl p-4"><p class="text-xs text-slate-500">Role</p><p class="font-bold mt-1">$role_tag</p></div><div class="bg-slate-50 rounded-xl p-4"><p class="text-xs text-slate-500">Location</p><p class="font-bold mt-1">$loc</p></div><div class="bg-slate-50 rounded-xl p-4"><p class="text-xs text-slate-500">Experience</p><p class="font-bold mt-1">$candidate / $exp_years</p></div><div class="bg-slate-50 rounded-xl p-4"><p class="text-xs text-slate-500">Eligible Batch</p><p class="font-bold mt-1">$batch</p></div><div class="bg-slate-50 rounded-xl p-4"><p class="text-xs text-slate-500">Salary / Stipend</p><p class="font-bold mt-1">$salary</p></div></div></div>
<div class="card bg-white border border-slate-200 rounded-2xl p-5 sm:p-6"><h2 class="text-xl font-black"><i class="fa-solid fa-circle-check text-[var(--primary)] mr-2"></i>Eligibility</h2><p class="mt-4 text-slate-600 leading-relaxed">$elig</p></div>
<div class="card bg-white border border-slate-200 rounded-2xl p-5 sm:p-6"><h2 class="text-xl font-black"><i class="fa-solid fa-list-check text-[var(--primary)] mr-2"></i>Responsibilities</h2><ul class="mt-4 space-y-3 text-slate-600">$responsibilities</ul></div>
<div class="card bg-white border border-slate-200 rounded-2xl p-5 sm:p-6"><h2 class="text-xl font-black"><i class="fa-solid fa-route text-[var(--primary)] mr-2"></i>How to Apply</h2><div class="mt-4 space-y-3"><div class="flex gap-3"><span class="w-7 h-7 rounded-full bg-[var(--primary)] text-white text-xs font-black flex items-center justify-center shrink-0">1</span><p class="text-slate-600">Open the official $company careers or recruitment website.</p></div><div class="flex gap-3"><span class="w-7 h-7 rounded-full bg-[var(--primary)] text-white text-xs font-black flex items-center justify-center shrink-0">2</span><p class="text-slate-600">Verify the latest role, eligibility, location and deadline information.</p></div><div class="flex gap-3"><span class="w-7 h-7 rounded-full bg-[var(--primary)] text-white text-xs font-black flex items-center justify-center shrink-0">3</span><p class="text-slate-600">Complete the application only through the official instructions.</p></div></div><a href="$apply" target="_blank" rel="noopener" class="mt-5 inline-flex items-center justify-center bg-green-500 hover:bg-green-600 text-white font-extrabold px-6 py-3 rounded-xl">Continue to Official Website <i class="fa-solid fa-arrow-up-right-from-square ml-2"></i></a></div>
<div class="rounded-2xl bg-amber-50 border border-amber-200 p-5 text-sm text-amber-900"><p class="font-extrabold"><i class="fa-solid fa-triangle-exclamation mr-1"></i> Important</p><p class="mt-1 leading-relaxed">HD Careers is an independent job information platform. Verify the latest job details on the official company website before applying. HD Careers does not charge candidates for applications.</p></div>
</div>
<aside class="space-y-5 lg:sticky lg:top-24">
<div class="card bg-white border border-slate-200 rounded-2xl p-5"><div class="flex items-center gap-3"><div class="w-14 h-14 rounded-xl border border-slate-200 bg-white flex items-center justify-center overflow-hidden"><img src="$favicon_url" alt="$company logo" class="w-[72%] h-[72%] object-contain" $logo_onerror></div><div><h3 class="font-black text-lg">Job Summary</h3><p class="text-xs text-slate-500">$company</p></div></div><div class="mt-4 divide-y divide-slate-100 text-sm"><div class="py-3 flex justify-between gap-4"><span class="text-slate-500">Category</span><span class="font-bold text-right">$cat_label</span></div><div class="py-3 flex justify-between gap-4"><span class="text-slate-500">Candidate</span><span class="font-bold text-right">$candidate</span></div><div class="py-3 flex justify-between gap-4"><span class="text-slate-500">Experience</span><span class="font-bold text-right">$exp_years</span></div><div class="py-3 flex justify-between gap-4"><span class="text-slate-500">Location</span><span class="font-bold text-right">$location_filter</span></div><div class="py-3 flex justify-between gap-4"><span class="text-slate-500">Posted</span><span class="font-bold text-right">$date</span></div></div><a href="$apply" target="_blank" rel="noopener" class="mt-4 block text-center bg-[var(--primary)] hover:bg-[var(--primary2)] text-white font-extrabold py-3 rounded-xl">Apply on Official Site</a></div>
<div class="rounded-2xl p-5 text-white" style="background:linear-gradient(135deg,#0f9d58,#128c4c)"><div class="w-11 h-11 rounded-xl bg-white/15 flex items-center justify-center text-xl"><i class="fa-brands fa-whatsapp"></i></div><h3 class="font-black text-lg mt-3">Get the next job first</h3><p class="text-sm text-green-50 mt-1">Join HD Careers for quick job alerts.</p><a href="https://whatsapp.com/channel/0029VamZKemKLaHrHF8Mwc3I" target="_blank" rel="noopener" class="mt-4 block text-center bg-white text-green-700 font-bold py-2.5 rounded-xl">Join WhatsApp</a></div>
<div class="card bg-white border border-slate-200 rounded-2xl p-5"><h3 class="font-black">Need help?</h3><a href="mailto:helpdeskinreallife@gmail.com" class="text-sm text-[var(--primary)] font-semibold mt-2 block break-all">helpdeskinreallife@gmail.com</a><div class="flex gap-2 mt-4"><a href="https://instagram.com/hd_careers" target="_blank" rel="noopener" class="w-10 h-10 rounded-xl bg-pink-50 text-pink-600 flex items-center justify-center"><i class="fa-brands fa-instagram"></i></a><a href="https://t.me/HD_Careers" target="_blank" rel="noopener" class="w-10 h-10 rounded-xl bg-sky-50 text-sky-600 flex items-center justify-center"><i class="fa-brands fa-telegram"></i></a><a href="https://whatsapp.com/channel/0029VamZKemKLaHrHF8Mwc3I" target="_blank" rel="noopener" class="w-10 h-10 rounded-xl bg-green-50 text-green-600 flex items-center justify-center"><i class="fa-brands fa-whatsapp"></i></a></div></div>
</aside>
</section>
</main>
<footer class="bg-[var(--dark)] text-slate-300 mt-4"><div class="max-w-6xl mx-auto px-4 py-7 flex flex-col sm:flex-row justify-between gap-4 text-sm"><div><p class="text-white font-black">HD Careers</p><p class="text-slate-400 text-xs mt-1">Jobs, internships, apprenticeships and career updates across India.</p></div><div class="flex flex-wrap gap-4"><a href="../index.html" class="hover:text-white">Home</a><a href="mailto:helpdeskinreallife@gmail.com" class="hover:text-white">Contact</a><a href="https://t.me/HD_Careers" target="_blank" rel="noopener" class="hover:text-white">Telegram</a></div></div></footer>
<div id="toast" class="hidden fixed bottom-5 left-1/2 -translate-x-1/2 bg-slate-900 text-white text-sm font-semibold px-4 py-2.5 rounded-full shadow-2xl z-50"></div>
<script>
const revealObserver=('IntersectionObserver' in window)?new IntersectionObserver((entries)=>{entries.forEach(entry=>{if(entry.isIntersecting){entry.target.classList.add('is-visible');revealObserver.unobserve(entry.target)}})},{threshold:.12,rootMargin:'0px 0px -30px 0px'}):null;
function initReveal(){document.querySelectorAll('.card, aside > div, .hero .bg-white\\/10, .rounded-2xl.bg-amber-50').forEach((el,i)=>{el.classList.add('reveal-on-scroll');el.style.setProperty('--reveal-delay',Math.min(i%5,4)*45+'ms');if(revealObserver)revealObserver.observe(el);else el.classList.add('is-visible')})}
initReveal();
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

        if not isinstance(job["resp"], list) or not job["resp"]:
            raise SystemExit(f"Job id {job['id']} must have at least one responsibility")

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


def logo_onerror(company: str) -> str:
    filename = LOCAL_LOGOS.get(company)
    if filename:
        return (
            "onerror=\"this.onerror=null;"
            f"this.src='../assets/logos/{esc(filename)}';"
            "this.className='w-[90%] h-[90%] object-contain'\""
        )
    return "onerror=\"this.style.display='none'\""


def render_job_page(job: dict) -> str:
    company = str(job["company"])
    role = str(job["role"])
    heading = f"{company} {role}"
    page_title = f"{heading} | HD Careers"
    candidate = "Fresher" if job["expType"] == "fresher" else "Experienced"
    cat = str(job["cat"])
    favicon_url = f"https://www.google.com/s2/favicons?domain={esc(job['domain'])}&sz=128"
    meta_description = (
        f"{heading} - location, eligibility, experience and official application link on HD Careers."
    )
    share_text = f"{company} - {role}\\n{job['loc']}"

    values = {
        "page_title": esc(page_title),
        "meta_description": esc(meta_description),
        "breadcrumb": esc(CAT_BREADCRUMB[cat]),
        "breadcrumb_job": esc(f"{company} {job['roleTag']}"),
        "favicon_url": favicon_url,
        "company": esc(company),
        "logo_onerror": logo_onerror(company),
        "cat_icon": CAT_ICON[cat],
        "cat_label": esc(CAT_LABEL[cat]),
        "candidate": candidate,
        "salary": esc(job["salary"]),
        "heading": esc(heading),
        "loc": esc(job["loc"]),
        "batch": esc(job["batch"]),
        "date": esc(job["date"]),
        "apply": esc(job["apply"]),
        "desc": esc(job["desc"]),
        "role_tag": esc(job["roleTag"]),
        "exp_years": esc(job["expYears"]),
        "elig": esc(job["elig"]),
        "responsibilities": render_responsibilities(job["resp"]),
        "location_filter": esc(job["locationFilter"]),
        "share_title": json.dumps(page_title, ensure_ascii=False),
        "share_text": json.dumps(share_text, ensure_ascii=False),
    }

    return PAGE_TEMPLATE.substitute(values)


def update_index(jobs: list[dict], dry_run: bool) -> bool:
    source = INDEX_FILE.read_text(encoding="utf-8")
    start_marker = "const JOBS = ["
    end_marker = "\n];\n\nconst CATS="

    start = source.find(start_marker)
    if start == -1:
        raise SystemExit("Could not find 'const JOBS = [' in index.html")

    end = source.find(end_marker, start)
    if end == -1:
        raise SystemExit("Could not find the end of the JOBS array in index.html")

    jobs_json = json.dumps(jobs, ensure_ascii=False, indent=2)
    replacement = "const JOBS = " + jobs_json
    updated = source[:start] + replacement + source[end + 3:]

    if updated == source:
        return False

    if not dry_run:
        INDEX_FILE.write_text(updated, encoding="utf-8")
    return True


def write_job_pages(jobs: list[dict], dry_run: bool) -> tuple[int, int]:
    created = 0
    changed = 0

    for job in jobs:
        target = ROOT / job["page"]
        output = render_job_page(job)

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

    return created, changed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate HD Careers homepage job data and individual job pages from data/jobs.json."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing files.",
    )
    args = parser.parse_args()

    jobs = load_jobs()
    index_changed = update_index(jobs, args.dry_run)
    created, changed = write_job_pages(jobs, args.dry_run)

    mode = "DRY RUN" if args.dry_run else "DONE"
    print(f"[{mode}] {len(jobs)} jobs loaded")
    print(f"index.html: {'would update' if args.dry_run and index_changed else 'updated' if index_changed else 'no change'}")
    print(f"job pages: {created} new, {changed} updated")

    if not args.dry_run:
        print("Run: python3 generate.py")


if __name__ == "__main__":
    main()
