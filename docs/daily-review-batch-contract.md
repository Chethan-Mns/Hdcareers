# HD Careers 9 AM discovery → Admin Review Center contract

**The 9 AM ChatGPT automation is the discovery orchestrator. The website does NOT invent its shortlist from /data/review-queue.json.** That queue belongs to the separate expired/unconfirmed-job checker. The only authoritative daily discovery Review Center state is `data/daily-review-batch.json`, read/written by `/api/admin/daily-batch`.

## Required producer behavior

1. At 9 AM IST, search authoritative employer careers pages; screen 30+ candidates when possible and compare against `data/jobs.json` for duplicate official URL, company+requisition, or company+role. Respect the user's manual closure decisions. If exact official job evidence is blocked, label UNCONFIRMED; never infer ACTIVE or EXPIRED from a crawler denial.
2. Rank up to 10 **priority** and up to 10 **backup** candidates; use actual discovered jobs only. Prefer fresher IT and recognizable companies while avoiding repeated employers in the Top 10. If fewer are found, **store the smaller list** and explain that publishing requires 10; never invent fillers.
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

## Publishing pipeline

The Owner or authorized Admin opens `/admin/review-batch.html`, checks official links and chooses **Live**, **Expired** or **Unsure**. Replace any expired priority listing with an already-reviewed LIVE backup in the same category. Submitting requires exactly 10 unique employers with 10 LIVE complete job objects and user confirmation.

The existing `/api/admin/publish` endpoint dispatches `admin_publish_jobs`. `.github/workflows/admin-job-generator.yml` rechecks each job and fails the full approved batch if anything is unconfirmed/expired, generates/commits the website, then calls `scripts/publish_approved_telegram.py` and saves individual Telegram receipts. **A dispatch acceptance is not proof of website deployment or Telegram delivery.** Monitor GitHub Actions and Vercel and report failures explicitly.

The `data/review-queue.json` used by expired job checker is intentionally independent and must not be overwritten by the daily discovery workflow.

Validation: `python3 scripts/validate_daily_review_batch.py`.

## Manual recovery and backfill

Today's historical ChatGPT shortlist is not a trusted source until its exact job URLs and verification evidence can be recovered. Do not fabricate rows to make the Review Center look full; rerun the discovery automation to generate and save a new verifiable batch.
