#!/usr/bin/env python3
"""Human-readable, read-only status and duplicate audit for official ATS discoveries.

This never updates employer/job status or the Admin queue. It distinguishes
exact official ATS confirmation from missing, inaccessible, or partial scans.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from discovery_ats_shadow import canonical, parse_board, clean_html
from check_job_availability import check, official_inventory_probe

STATUS = {"active": "Live", "expired": "Expired", "review": "Needs Review"}
SOURCES = ("Published website", "Current Admin batch", "Review queue", "Earlier discovery draft")


def canonical_employer(value):
    name = " ".join(str(value or "").casefold().replace("&", "and").split())
    return {"deloitte usi": "deloitte", "deloitte south asia": "deloitte",
            "ey": "ernst and young", "ernst & young": "ernst and young",
            "pwc india": "pwc", "tcs": "tata consultancy services"}.get(name, name)


def normalized_pair(item):
    return (canonical_employer(item.get("company")),
            clean_html(item.get("role")).casefold(),
            clean_html(item.get("loc") or item.get("location")).casefold())


def expand_sources(published, batch, queue, drafts):
    records = []
    for source, items in [
        ("Published website", published),
        ("Current Admin batch", list(batch.get("priority", [])) + list(batch.get("backup", []))),
        ("Review queue", queue),
        ("Earlier discovery draft", drafts),
    ]:
        for item in items:
            if not isinstance(item, dict):
                continue
            job = item.get("job") if isinstance(item.get("job"), dict) else item
            row = {**item, **job}
            url = row.get("apply") or row.get("url")
            if url:
                records.append((source, row, url))
    return records


def duplicate_verdict(candidate, records, history=None):
    """Do not conflate title similarity with an exact requisition duplicate."""
    url = canonical(candidate.get("apply"))
    if not url:
        return ("Needs Review", "Invalid or missing official apply URL")
    pair = normalized_pair(candidate)
    for source, row, raw in records:
        if url == canonical(raw):
            return ("Duplicate", "Exact official apply URL in " + source)
    history = history or {}
    seen = history.get("jobs", {})
    if candidate.get("id") in seen:
        return ("Previously Seen", "Same ATS requisition recorded in discovery history")
    for row in seen.values():
        if url == canonical(row.get("apply")):
            return ("Previously Seen", "Same official URL recorded in discovery history")
    for source, row, raw in records:
        if normalized_pair(row) == pair and all(pair):
            return ("Possible Duplicate", "Same employer, role and location in " + source + "; confirm requisition ID")
    return ("New", "No exact URL or known ATS-ID match in available website, batch, queue or history")


def probe_official(candidate):
    """One exact public ATS inventory check, or conservative Workday page check."""
    try:
        provider = candidate.get("sourceProvider")
        if provider == "workday":
            result = check({"id": candidate.get("id"), "company": candidate.get("company"),
                            "role": candidate.get("role"), "apply": candidate.get("apply")})
            return result["state"], result["reason"]
        if provider not in {"greenhouse", "lever", "ashby", "smartrecruiters"}:
            return "review", "Unsupported ATS provider; verify the job-bound employer page manually"
        probe = official_inventory_probe({"role": candidate.get("role"),
                                          "apply": candidate.get("apply")})
        if probe is None:
            return "review", "No exact ATS inventory verification supported"
        return probe
    except Exception as exc:
        return "review", "ATS verification failed (" + type(exc).__name__ + "); manual check needed"


def inspect(report, *, published, batch, queue, drafts, history=None,
            verifier=probe_official, max_verify=60):
    if (report.get("mode") != "shadow_only" or report.get("profile") != "fresher"
        or report.get("publicationAllowed") is not False
        or report.get("expiryDecisionsAllowed") is not False):
        raise ValueError("Only read-only website-fresher discovery can be audited")
    candidates = report.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != report.get("candidateCount"):
        raise ValueError("Discovery candidate count invalid")
    if not isinstance(max_verify, int) or not 0 <= max_verify <= 200:
        raise ValueError("Verification budget must be 0..200")
    records = expand_sources(published, batch, queue, drafts)
    checked_at = datetime.now(timezone.utc).isoformat()
    rows = []
    for idx, candidate in enumerate(candidates):
        status, reason = duplicate_verdict(candidate, records, history)
        if idx < max_verify:
            state, evidence = verifier(candidate)
        else:
            state, evidence = "review", "Not independently checked: run verification limit reached"
        if state not in STATUS:
            state, evidence = "review", "Unexpected verification status; held for review"
        rows.append({
            "company": candidate.get("company", ""),
            "role": candidate.get("role", ""),
            "location": candidate.get("loc", ""),
            "officialUrl": candidate.get("apply", ""),
            "source": candidate.get("sourceProvider", ""),
            "atsId": candidate.get("externalId", ""),
            "availability": STATUS[state],
            "availabilityEvidence": str(evidence),
            "duplicate": status, "duplicateEvidence": reason,
            "eligibleForPublishing": False, "ownerVerificationRequired": True,
        })
    # The source scanner deliberately excludes exact website duplicates; show
    # those too without implying their live availability was checked.
    for removed in report.get("excludedCandidates", []):
        if removed.get("duplicateReason") not in {"site", "in_run"}:
            continue
        rows.append({
            "company": removed.get("company", ""), "role": removed.get("role", ""),
            "location": removed.get("loc", ""), "officialUrl": removed.get("apply", ""),
            "source": removed.get("sourceProvider", ""), "atsId": removed.get("externalId", ""),
            "availability": "Needs Review",
            "availabilityEvidence": "Excluded during discovery; no independent exact-job check run",
            "duplicate": "Duplicate",
            "duplicateEvidence": ("Already on published HD Careers site" if removed["duplicateReason"] == "site"
                                  else "Duplicate official requisition within current discovery run"),
            "eligibleForPublishing": False, "ownerVerificationRequired": True,
        })
    stats = {
        "checkedAt": checked_at, "extractedCandidates": len(candidates),
        "verifiedCandidates": min(len(candidates), max_verify),
        "displayedRows": len(rows),
        "live": sum(r["availability"] == "Live" for r in rows),
        "expired": sum(r["availability"] == "Expired" for r in rows),
        "needsReview": sum(r["availability"] == "Needs Review" for r in rows),
        "duplicate": sum(r["duplicate"] == "Duplicate" for r in rows),
        "previouslySeen": sum(r["duplicate"] == "Previously Seen" for r in rows),
        "possibleDuplicate": sum(r["duplicate"] == "Possible Duplicate" for r in rows),
        "new": sum(r["duplicate"] == "New" for r in rows),
        "safeAutoPublish": False,
    }
    return {
        "mode": "owner_availability_duplicate_review_only", "summary": stats,
        "publicationAllowed": False, "expiryDecisionsAllowed": False,
        "notes": [
            "Live means the exact public ATS posting was returned by an official inventory or convincing job-page evidence; opening the employer form and confirming requirements remains a manual step.",
            "An incomplete/failed ATS scan, 404, robots challenge, unavailable page or absence from a filtered list is NEVER automatically marked Expired.",
            "The source scanner already removes known website duplicates; excluded records are shown separately when recorded.",
            "Previously Seen reflects persistent history only if the ledger is stored across runs; a fresh empty ledger cannot identify older unseen discoveries.",
            "Possible Duplicate must be reviewed because distinct requisitions can share a role and location.",
            "All classifications are read-only and need owner verification before HD Careers Admin submission.",
        ],
        "rows": rows,
    }


def write_csv(path, rows):
    fields = ["company", "role", "location", "availability", "availabilityEvidence",
              "duplicate", "duplicateEvidence", "officialUrl", "source", "atsId"]
    with Path(path).open("w", newline="", encoding="utf-8-sig") as out:
        writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_html(path, report):
    """Self-contained offline browser report; no external scripts or fonts."""
    stats = report["summary"]
    esc = lambda x: html.escape(str(x or ""), quote=True)
    markup = []
    for row in report["rows"]:
        url = row["officialUrl"]
        safe = canonical(url)
        link = (f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">Open official job</a>'
                if safe else "Invalid link")
        markup.append(
            '<tr data-search="' + esc(" ".join(str(v) for v in row.values()).casefold()) + '">'
            + "".join("<td>" + esc(row[field]) + "</td>" for field in ("company", "role", "location"))
            + '<td><span class="pill">' + esc(row["availability"]) + '</span><small>' + esc(row["availabilityEvidence"]) + '</small></td>'
            + '<td><span class="pill">' + esc(row["duplicate"]) + '</span><small>' + esc(row["duplicateEvidence"]) + '</small></td>'
            + "<td>" + link + "</td></tr>"
        )
    page = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>HD Careers — Official ATS Job Verification</title>
<style>
:root{color-scheme:dark}*{box-sizing:border-box}
body{margin:0;background:#081830;color:#edf4ff;font:15px/1.5 system-ui,-apple-system,sans-serif}
main{max-width:1280px;margin:auto;padding:28px 20px}
h1{margin:0;font-size:30px}h2{font-size:17px}p,.muted,small{color:#b3c8e9}
.cards{display:flex;flex-wrap:wrap;gap:12px;margin:22px 0}
.card{background:#102b52;border:1px solid #355578;border-radius:12px;padding:13px 18px;min-width:120px}
.card b{display:block;font-size:25px}
input,select{padding:12px;border:1px solid #4c6f99;border-radius:8px;background:#102b52;color:white}
.controls{display:flex;gap:10px;flex-wrap:wrap;margin:22px 0}
table{width:100%;border-collapse:collapse;min-width:850px}
th{text-align:left;color:#a8cbed;background:#102b52}
th,td{border-bottom:1px solid #294b76;padding:13px 10px;vertical-align:top}
tbody tr:nth-child(even){background:#0d2342}
td small{display:block;margin-top:6px;max-width:330px;overflow-wrap:anywhere}
.pill{display:inline-block;border:1px solid #729cce;padding:2px 8px;border-radius:999px}
a{color:#83c6ff} .scroll{overflow-x:auto}
</style></head><body><main>
<h1>HD Careers — Discovery Job Verification</h1>
<p>Read-only official ATS discovery check. Results are evidence-based, not owner approval. Nothing is published or expired automatically.</p>
<div class="cards">__CARDS__</div>
<div class="controls">
<input id="search" type="search" placeholder="Search company, role, location or reason" aria-label="Search jobs">
<select id="availability" aria-label="Availability filter"><option value="">All availability</option><option>Live</option><option>Expired</option><option>Needs Review</option></select>
<select id="duplicate" aria-label="Duplicate filter"><option value="">All duplicate statuses</option><option>New</option><option>Duplicate</option><option>Previously Seen</option><option>Possible Duplicate</option></select>
</div>
<p id="shown" aria-live="polite"></p>
<div class="scroll"><table><thead><tr><th>Company</th><th>Role</th><th>Location</th><th>Availability + reason</th><th>Duplicate + reason</th><th>Apply</th></tr></thead>
<tbody>__ROWS__</tbody></table></div>
<h2>How to interpret results</h2><p>Live: exact official ATS posting confirmed by an independent check; application and eligibility still need owner verification. Expired: explicit authoritative closure or expired deadline. Needs Review: inconclusive, unverified or failed checks. Duplicate and Previously Seen jobs must not be automatically submitted. This file works offline and does not change Admin, website or Telegram.</p>
</main><script>
const a=document.getElementById('availability'),d=document.getElementById('duplicate'),q=document.getElementById('search'),shown=document.getElementById('shown');
function filter(){let n=0;for(const tr of document.querySelectorAll('tbody tr')){let cells=tr.querySelectorAll('td');let ok=(!a.value||cells[3].querySelector('.pill').textContent===a.value)&&(!d.value||cells[4].querySelector('.pill').textContent===d.value)&&tr.getAttribute('data-search').includes(q.value.trim().toLowerCase());tr.hidden=!ok;if(ok)n++;}shown.textContent=n+' jobs shown';}
a.addEventListener('change',filter);d.addEventListener('change',filter);q.addEventListener('input',filter);filter();
</script></body></html>"""
    cards = "".join('<div class="card"><b>'+esc(stats[k])+'</b>'+esc(label)+'</div>' for k,label in
        (("live","Live"),("expired","Expired"),("needsReview","Needs Review"),
         ("new","New"),("duplicate","Duplicate"),("previouslySeen","Previously Seen"),
         ("possibleDuplicate","Possible Duplicate")))
    Path(path).write_text(page.replace("__CARDS__", cards).replace("__ROWS__", "\n".join(markup)), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--jobs", default=str(ROOT / "data/jobs.json"))
    ap.add_argument("--batch", default=str(ROOT / "data/daily-review-batch.json"))
    ap.add_argument("--queue", default=str(ROOT / "data/review-queue.json"))
    ap.add_argument("--history", default=str(ROOT / "data/ats-discovery-history.json"))
    ap.add_argument("--draft", default="")
    ap.add_argument("--verify-limit", type=int, default=60)
    ap.add_argument("--output-prefix", default="ats-job-status")
    args = ap.parse_args()
    load = lambda p, fallback: json.loads(Path(p).read_text(encoding="utf-8")) if p and Path(p).is_file() else fallback
    draft = load(args.draft, [])
    drafts = draft.get("items", []) if isinstance(draft, dict) else (draft if isinstance(draft, list) else [])
    result = inspect(load(args.report, {}), published=load(args.jobs, []),
                     batch=load(args.batch, {}), queue=load(args.queue, []),
                     drafts=drafts, history=load(args.history, {}),
                     max_verify=args.verify_limit)
    prefix = args.output_prefix
    Path(prefix + ".json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(prefix + ".csv", result["rows"])
    write_html(prefix + ".html", result)
    print(json.dumps(result["summary"], indent=2))
    print("Open "+prefix+".html to filter Live/Expired/Needs Review and Duplicate/New")


if __name__ == "__main__":
    main()
