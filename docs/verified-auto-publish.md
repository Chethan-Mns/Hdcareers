# HD Careers — Verified automatic daily publishing

The 9 AM IST discovery automation searches Deloitte first, the other watchlisted employers, and then additional official employer/ATS sites if vacancies remain. It stages Priority 10 + Backup 10, each *targeting* **6 technical full-time, 2 non-IT full-time, and 2 internship/apprenticeship** roles. Discovery may produce fewer than 20 when source verification fails; never fabricate vacancies.

At 11:30 AM IST, `.github/workflows/verified-auto-publish.yml` automatically selects from Priority **then** Backup, applying the **same strict 6/2/2 per-category caps** to the final publication batch. The worker does not require daily Admin selection or a manual Live click; it only considers newly discovered, fresh, exact official-source-confirmed roles with complete source-grounded content. If only 6 technical, 2 non-IT, and 1 internship qualify, it sends **9**, not 10. It never fills missing training slots with extra technical roles or treats internships as technical full-time jobs. Contradictory category, role and experience-type classifications are skipped, and internship/apprenticeship experience labels are preserved in the published record.

Availability must be `source-active`, independently verified within 18 hours using an approved proof phrase and source context. The selector excludes unsure, expired, stale, prior published or review-queue roles, inappropriate experienced roles, job boards instead of exact official employer postings, repeated requisitions and duplicate employers. Automatic publishing does not imply that every job in the daily discovery batch is eligible.

The selector writes a non-sensitive report with `categoryTargets`, `categoryCounts` and `categoryShortfalls`. Empty buckets are visible: **no fillers**. Existing idempotent batch claims are committed before publication dispatch; a failure after claim requires reconciliation rather than blindly posting duplicates.

After selection, the existing Admin Direct Publish pipeline rechecks the exact official application link, adds only still-live roles to the website, generates/commits pages, and enqueues Telegram. The first delivery follows website deployment checks, with remaining messages spaced hourly. The Whapi.Cloud relay (when configured and enabled) mirrors confirmed Telegram receipts into **HD Career Updates** on WhatsApp, subject to its own quota and verification checks. An external outage or incomplete source check can reduce the number of actual posts.

The expiry checker is separate from discovery: previously published expired or uncertain roles display **⚠️ Job may have expired — verify before applying**, and confirmed-expired pages do not claim applications are open. Uncertain jobs are not newly published.

Scheduled execution, Vercel readiness and messaging provider acceptance are not guaranteed outcomes. Inspect GitHub Actions, public pages and Telegram/WhatsApp receipts when validating a real production day.

Run `python3 -m unittest discover -s tests -p test_auto_verified_publish.py -v` to verify the selection quotas and safety cases. Do not use a previous day's already-claimed batch as a live dry-run; new batches must be new, source-verified and deduplicated.
