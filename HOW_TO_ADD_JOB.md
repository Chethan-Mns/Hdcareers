# How to Add a Job to HD Careers

## Source and verification rules

Use a specific, live job posting from the employer's official careers site or an authorized ATS/recruitment portal. Do not use a generic company careers homepage as the application URL when a specific posting exists.

Before publishing:
- Confirm the exact application URL opens the intended job.
- Confirm the role is still accepting applications.
- Copy only facts supported by the official posting.
- Never invent salary, batch, degree, experience, hiring volume or work mode.
- Use `Not Disclosed` for salary and `Not Specified` for other missing facts.
- Write an original HD Careers summary instead of copying long sections from the employer page.

## Required job fields

Copy `data/job-template.json` and complete every field.

Key verification fields:
- `status`: `active` or `expired`
- `verifiedDate`: date the official source was checked
- `sourceName`: e.g. `Official Citi Careers page`
- `skills`: skills actually supported by the posting
- `who`: a short factual explanation of the candidate profile that matches the posting
- `workMode`: Remote, Hybrid, On-site, or Not Specified

## Publishing steps

1. Add the verified job object near the top of `data/jobs.json`.
2. Use the next available numeric ID and a unique page path under `jobs/`.
3. Run:
   ```bash
   python3 generate.py --dry-run
   python3 generate.py
   ```
4. Verify:
   - homepage card
   - generated job page
   - eligibility, experience, location and salary labels
   - source and last-verified information
   - related jobs
   - official application link
   - `robots.txt` and `sitemap.xml`
5. Commit and review the preview before production.

## Expired jobs

When a previously valid job closes, do not continue showing it as active.

Set:
```json
"status": "expired"
```

Update `verifiedDate` to the date the closure was confirmed. The generator keeps a useful reference page, removes the active Apply action, shows an expired notice, and directs visitors to current jobs.

## Low-quality or unverified records

Remove records that cannot be tied to a specific, trustworthy job posting, especially seed/demo entries with:
- generic company career-homepage URLs
- guessed salary or batch information
- placeholder descriptions
- contradictory experience data
- no reliable official source

`data/jobs.json` remains the single source of truth. Do not manually maintain duplicate job data in generated pages.


## Availability checks

Use discovery sites only as leads. Verify the exact employer-owned job page or
employer-linked ATS tenant during discovery, immediately before publishing, and
again before sharing. A successful HTTP response alone does not prove an opening.
Do not substitute a generic careers page or bypass uncertain checks.

Run `python3 scripts/check_job_availability.py --before <base-commit>` before
publishing new, reopened or changed-source jobs. Admin publishing and both Telegram
entry points also require the same active result. A failed check stops the batch.
Inspect the failure rather than changing a job's metadata to bypass it.

Optional `closingAt` must be an official application deadline, expressed as ISO
8601 with a timezone, e.g. `2026-10-10T23:59:00+05:30`. Never infer it from the
posting date. Unknown deadlines remain absent.

The scheduled availability workflow runs around 08:15 and 20:15 IST (GitHub may
delay runs). It checks active jobs and expires only explicit closure messages or
passed official deadlines, then regenerates the existing closed-page UI and
active listings in one commit. Historical job URLs remain accessible. It does
not send new-job Telegram posts for closure updates or reopen expired jobs.

Each run uploads availability-report.json for 30 days and displays a review queue
in its Actions summary. DNS failures, timeouts, HTTP errors (including 404),
redirects, blocked pages and JavaScript-only pages require review; they do not
change an existing listing's status or verification date. This conservative
checker cannot verify every ATS: those sources need an adapter or manual review
and cannot be published through the automated gate until supported.

Status changes require a successful Git push and Vercel deployment to reach
production. Check the deployment after a closure commit; a scheduled run is not
a guarantee of an immediate website update.
