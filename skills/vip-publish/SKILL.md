---
name: hd-careers-vip-publish
description: Publish official, verified-live jobs to HD Careers and Telegram using the existing guarded GitHub Actions pipeline.
---

# HD Careers VIP publish

## User commands

- `VIP PUBLISH <official-job-url>`
- `Publish this job: <official-job-url>`
- `PUBLISH LIVE BATCH` (for the owner-reviewed shortlist; not every unreviewed item)

These are **natural-language commands** for an assistant with connected GitHub access, not a claim that a native ChatGPT slash command is installed. Two or three independent VIP jobs per day are supported by the existing one-job-per-request workflow; there is no queue.

## Execution contract

1. Take the exact official job URL. Never substitute a general careers homepage, a job board repost, or a different requisition.
2. Read `data/jobs.json`, `data/telegram-deliveries.json`, `data/review-queue.json` and today's `data/daily-review-batch.json`. Do not republish duplicate exact URLs, requisition IDs, company+role matches or delivered Telegram pages. Preserve earlier owner-expired decisions.
3. Research the official requisition to capture exact title, employer, location, candidate eligibility, type, responsibilities and application URL. Mark all unavailable fields `Not specified` / `Not Disclosed`. Do not invent batches, experience, skills, packages, deadlines or application availability.
4. Verify the **exact** requisition on the employer portal, preferably using official Greenhouse/Lever/SmartRecruiters/Ashby inventory where applicable, plus the specific job page and active application control. Match the job ID, not merely its title. Treat 403, captcha, rate limits, redirects, HTTP 404 alone, or insufficient Apply evidence as `review` instead of `expired`. Only mark `expired` with corroborated exact-ID employer closure or an authoritative closing deadline. A new posting under the same title is a different job.
5. If verified Live, prepare a complete single-job `admin_publish_jobs` event in `data/vip-publish-request.json` (see its latest example). Update the file on `main` using the current SHA. The `Admin Direct Publish` workflow handles the rest. If `review`, hold and request owner confirmation of the exact original application form, without publishing. Owner confirmation must be timestamped against the same exact URL. An explicit employer-confirmed closure is not overrideable by an older manual Live timestamp.
6. GitHub Actions `.github/workflows/admin-job-generator.yml` runs `scripts/admin_publish.py`, resolves logos, generates the website and manifest, commits generated pages to `main`, waits for the exact public HD Careers page, and invokes `scripts/publish_approved_telegram.py`. The approved Telegram manifest must identify only truly published pages. Do not send Telegram before the website is live.
7. After the workflow, check Vercel production deployment is READY for the generated commit; inspect the exact public page; verify the confirmed `delivered` receipt in `data/telegram-deliveries.json` including the Telegram `messageId`; clean any stale Needs Review entry only after website+Telegram delivery are recorded. Do not mark success from a GitHub commit alone.
8. Reply with source URL, HD Careers public job URL, exact Telegram message link/ID, and any exceptions. If the gate blocks, report the exact reason instead of claiming it posted.

## Daily publishing

- Evaluate the priority 10 and backup 10 for the saved review batch, at publication time.
- Only publish confirmed active postings with sufficiently complete, validated metadata. New unreviewed jobs are **not automatically owner approved** merely because a previous scan labeled them `live`.
- In approved batches, verified `active` jobs proceed, `review` jobs go to Needs Review and `expired` jobs are skipped. One questionable job must not block the independent Live jobs.
- Post each newly deployed job once to `@HD_Careers`, with a receipt. Never republish delivered entries without an explicit new reason.
- Keep failures and ambiguous deliveries in review; no blind Telegram retry.

## Safety and accuracy

The October 17 Wayfair Software Engineer Intern 20829 incident is the regression case: JSON-LD matched the job but the initial automated classification stopped at Review before evaluating the application control. Owner later verified the exact form, permitting guarded publication. Never assume JSON-LD by itself confirms an accepting application; inspect both structured and visible job evidence. Use `tests/test_job_availability.py` and `tests/test_admin_publish_partial.py` before releasing checker changes.
