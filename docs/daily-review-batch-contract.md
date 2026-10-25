# HD Careers 9 AM discovery → Admin Review Center contract

**The 9 AM ChatGPT automation is the discovery orchestrator. The website does NOT invent its shortlist from /data/review-queue.json.** That queue belongs to the separate expired/unconfirmed-job checker. The only authoritative daily discovery Review Center state is `data/daily-review-batch.json`, read/written by `/api/admin/daily-batch`.

## Required producer behavior

1. At 9 AM IST, prioritize Deloitte then search the 87 watchlisted employers on their authoritative careers pages, extending to remaining official portals and fallback employers if fewer than 20 qualify. Screen as many real exact requisitions as possible. The 9 AM agent filters against `data/jobs.json`, prior archived review batches, owner-confirmed expired URLs, and Telegram receipts; the CI pre-review scrub reruns duplicate checks even when only 1–14 candidates remain. Respect the user's manual closure decisions. If exact official job evidence is blocked, label UNCONFIRMED; never infer ACTIVE or EXPIRED from a crawler denial.
2. Rank up to 10 **Priority** and 10 **Backup**, independently targeting **6 fresher technical full-time + 2 fresher nontechnical + 2 internship/apprenticeship** roles in each list, across 20 distinct employers. Do not count IT internships as technical full-time work. If fewer real verified jobs exist, preserve a smaller deduplicated review batch, record per-category shortages, and do not invent fillers. Manual approval may publish 1–10 jobs.
3. For each item, include **full publication-ready** `job` details only if grounded in source evidence. If the full content is not available, preserve the partially filled `job` and `verificationReason` so the owner can still review it, but publishing remains blocked. Do not create fictional salary, batch, eligibility, degree, recruiter or posting date.
4. Create a unique batch ID for that day's run, e.g. `2026-10-11-0900-ist`, set `generatedAt` to an ISO timestamp, `status:"reviewing"`, `updatedAt` similarly, and add `priority` and `backup` arrays. Every item must begin with `reviewedStatus:"unreviewed"` (not LIVE), even if the website is evidently active; this ensures **human approval**. Store the automated/source verdict separately as `verificationVerdict`.
5. **Before sending any user-facing shortlist**, use the connected GitHub file API to read and update `Chethan-Mns/Hdcareers` **main** `data/daily-review-batch.json` using its current file blob SHA. GitHub update is the write source of truth. Read it back and confirm that the returned `batchId`, number of priority and backup items, and URLs match what was written.
6. Never overwrite an unresolved batch from another date without preserving it in an archive under `data/review-batch-archive/<old-batch-id>.json`. Use supported GitHub file tools. If archive/write/readback fails, **tell the user the review batch could not be saved**. Do not say it is available in Admin or that it was published.
7. The 9 AM automation is **discovery and staging only**. It must never call `/api/admin/publish`, write `data/jobs.json`, or prepare the Telegram-approved manifest before explicit approval.
8. Report with links `https://hdcareers.in/admin/review-batch.html`, counts, batch ID, exact source evidence and any incomplete-job warnings. Never claim production Vercel deployment succeeded unless verified.

## Candidate schema (representative values; DO NOT treat example as a live job)

```json
{
  "batchId": "2026-10-11-0900-ist",
  "generatedAt": "2026-10-11T03:30:00Z",
  "status": "reviewing",
  "priority": [
    {
      "id": "real-company-req-123",
      "company": "Actual employer",
      "role": "Official role",
      "loc": "Official location",
      "apply": "https://employer.example/jobs/123",
      "cat": "it",
      "expYears": "0–1 year",
      "reviewedStatus": "unreviewed",
      "verificationVerdict": "unconfirmed",
      "verificationReason": "Exact official application page returned a challenge; manual check required",
      "postedDate": null,
      "job": {
        "company": "Actual employer",
        "role": "Official role",
        "loc": "Official location",
        "apply": "https://employer.example/jobs/123",
        "status": "review"
      }
    }
  ],
  "backup": [],
  "updatedAt": "2026-10-11T03:30:00Z"
}
```

Only populate full `job` fields when supported. See `scripts/admin_publish.py` REQUIRED fields before considering a job publication-ready. A pending candidate should not be falsely made `status:"active"`. **Example domains are placeholders, never real shortlist items.**

## Pre-review duplicate screening and honest shortage reporting

`scripts/reprioritize_review_batch.mjs` now runs `filterDiscoveryDuplicates` before the quota ranking guards. New, unreviewed batches are screened for published exact URLs (including tracking-parameter variants), employer/requisition and company/role matches, prior reviewed exact requisitions, owner-confirmed expired URLs, Telegram deliveries and duplicate employer aliases. The result is saved as `discoveryAudit` including exclusion records, remaining slots and category shortfalls. An incomplete batch passes shortage-aware discovery validation; a complete 20-job batch must satisfy the 6/2/2 quotas. Already-reviewed/submitted/published batches are immutable under this automatic process.

A target of 20 is not a guarantee that 20 open fresher-qualified official requisitions exist. Discovery must report actual visited/unvisited employers, blocked checks and genuine vacancies; never invent jobs or claim 87 portals were visited without evidence.

## Publishing pipeline

The Owner or authorized Admin opens `/admin/review-batch.html`, checks official links and chooses **Live**, **Expired** or **Unsure**. Replace any expired priority listing with an already-reviewed LIVE backup in the same category. Submitting allows 1–10 unique employer jobs only when manually reviewed Live, source-complete and explicitly selected by the owner. When fewer than 10 qualified postings exist, publish only approved valid jobs instead of inventing jobs.

The existing `/api/admin/publish` endpoint dispatches `admin_publish_jobs`. `.github/workflows/admin-job-generator.yml` rechecks each job, holds source-unconfirmed candidates and skips confirmed-closed jobs without blocking other approved verified jobs. It generates/commits the website and enqueues all new pages for Telegram. For multi-job batches, the first item posts after its production website page is verified Live; later posts are sent one per hour from confirmed delivery receipts. Single-job VIP publication can post immediately. **A dispatch acceptance is not proof of website deployment or Telegram delivery.** Monitor GitHub Actions and Vercel and report failures explicitly.

The `data/review-queue.json` used by expired job checker is intentionally independent and must not be overwritten by the daily discovery workflow.

Validation: `python3 scripts/validate_daily_review_batch.py`.

## Manual recovery and backfill

Today's historical ChatGPT shortlist is not a trusted source until its exact job URLs and verification evidence can be recovered. Do not fabricate rows to make the Review Center look full; rerun the discovery automation to generate and save a new verifiable batch.
