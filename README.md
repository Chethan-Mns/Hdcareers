# HD Careers (hdcareers.in)

HD Careers is a mobile-first Indian jobs platform combining static job pages, official-source verification, Vercel production hosting, an authenticated web admin, a privately signed Android admin app, GitHub Actions publishing, hourly Telegram announcements, and GA4/Clarity analytics. A separate iOS simulator project is retained.

Production: https://hdcareers.in

_Last refreshed and verified against the production repository: 18 Oct 2026. GitHub workflow/queue/receipt state is authoritative for current delivery status._

## Current Architecture

~~~text
Public jobs website (index.html, jobs/, insights/, generate.py)
    ↑
data/jobs.json + official-source availability checks
    ↑
Owner / Job Editor authenticated web admin (/admin/)
    ├── Daily Review Center: 10 priority + 10 backup
    ├── Expiry Checker: Live / Expired / Unsure
    ├── Explicit Publish Ready + per-job publishing tracker
    ├── VIP job editor, Reel Kit, analytics, team controls
    └── Android Admin v1.3.2: Home / Review / Jobs / More
         |
Approved verified jobs → GitHub Actions coordinated publisher
         |
GitHub main commit → Vercel → verified public HD Careers pages
         |
Multi-job approved batch: first Telegram post immediately
    → remaining posts hourly after each real delivery
    → self-waking GitHub relay with five-minute cron backup
    → saved queue state and Telegram message receipts
         |
Admin job-card progress + Firebase/Android notifications
~~~

| Area | Implemented paths |
| --- | --- |
| Public site | index.html, jobs/, insights/, assets/, generate.py |
| Canonical jobs & job content | data/jobs.json, data/job-template.json |
| Daily owner reviews | data/daily-review-batch.json, admin/review-batch.html, api/admin/daily-batch.js |
| Admin web dashboard | admin/index.html, admin/traffic.html, admin/team.html, admin/reel-kit.html |
| Expiry/new-job review | data/review-queue.json, data/availability-status.json, api/admin/availability.js, api/admin/review.js |
| Guarded publishing + tracker | api/admin/publish.js, .github/workflows/admin-job-generator.yml |
| Hourly Telegram queue | scripts/hourly_telegram.py, data/telegram-hourly-queue.json, data/telegram-deliveries.json |
| Self-waking scheduler | .github/workflows/hourly-telegram-queue.yml, data/telegram-scheduler-kick.json |
| Native Android Admin | android-admin/, android-admin/app/src/main/java/in/hdcareers/admin/ |
| Android builds | .github/workflows/android-admin-build.yml, .github/workflows/android-admin-private-release.yml |
| Push notifications | lib/admin-push-handler.js, .github/workflows/android-review-notify.yml, .github/workflows/android-expiry-notify.yml |
| Quality/security checks | tests/, .github/workflows/review-lifecycle-check.yml, .github/workflows/telegram-hourly-regression.yml |

## Public Website Features

- Latest jobs, internships, apprenticeships, off-campus drives, remote roles, walk-ins, experienced jobs, government jobs and non-IT jobs
- Search by role, company, skill and related job information
- Filters for category, level, experience, role, company and location
- Automatic scroll to updated results after search/filter changes
- SEO-friendly individual job pages under `/jobs/`
- Official employer application links
- Dynamic official-company logos with cached local assets and fallbacks
- Consistent public header/navigation across public pages
- Job sharing using HD Careers job-page URLs
- Responsive mobile-first UI with desktop layout tuning
- WhatsApp, Instagram and Telegram links
- Resume-to-JD matching / score checker
- Career Resources and Insights content
- Crawlable About, Contact, Privacy Policy, Terms and Disclaimer pages
- `robots.txt` and `sitemap.xml` generation
- Google Analytics 4 and Microsoft Clarity tracking

## Admin Features

The protected HD Careers Admin currently supports job publishing/maintenance, availability review and traffic monitoring.

The traffic dashboard now exposes a denser operational view including:

- Realtime users
- Users, page views and sessions
- New and returning users
- Engaged sessions and engagement rate
- Average session duration
- Views per user and views per session
- Daily traffic trends
- Top pages and referrers
- Traffic channels
- Countries and devices
- Job-page views
- Apply clicks and apply rate
- Resume checks
- Shares and social clicks
- Top apply jobs, resume jobs and apply sources

Uncertain availability results are surfaced through the review workflow rather than being silently treated as expired.

## Job Data

`data/jobs.json` is the single source of truth for job listings.

Do not manually maintain duplicate job content in generated pages. A reusable object is available at:

```
data/job-template.json
```

Important operational state is stored separately:

- `data/availability-status.json` — latest availability-check summary
- `data/review-queue.json` — jobs that require human/browser review
- `data/telegram-approved-batch.json` — approved delivery manifests
- `data/telegram-deliveries.json` — message receipts and safe retry state
- `data/automation-status.json` — automation health/status
- `data/company-logos.json` — resolved company-logo manifest

## Job Verification

Publishing uses conservative official-source verification.

The checker in `scripts/check_job_availability.py`:

1. Requires public HTTPS job URLs.
2. Checks explicit `closingAt` deadlines when provided.
3. Looks for the exact role/verification terms and application controls.
4. Detects explicit closure language, access challenges and redirects.
5. Uses both browser-compatible and automation-oriented requests for dynamic career sites.
6. Treats conflicting browser/bot representations as uncertain instead of blindly expiring a job.
7. Allows a fresh `browserVerifiedAt` verification to override an inconclusive/conflicting automated result for 24 hours.
8. Sends uncertain new listings to `data/review-queue.json`.
9. Prunes only the bad/unverified new listing during a multi-job publish instead of failing the entire valid batch.
10. Marks jobs expired automatically only when closure evidence is sufficiently reliable.

This matters for modern career portals that can return different content to a real browser and a crawler. A crawler-only fallback must not be treated as definitive closure when stronger browser evidence conflicts with it.

Published-job availability checks run twice daily at approximately:

- 08:15 IST
- 20:15 IST

The availability workflow also runs a content-quality audit and retains reports as GitHub Actions artifacts.

## Generate the Site

Preview changes:

```bash
python3 generate.py --dry-run
```

Generate/update the site:

```bash
python3 generate.py
```

The generator updates active job data, individual job pages, crawl files and related generated website content.

## Add a New Job

Recommended workflow:

1. Find the exact official employer/recruitment page.
2. Confirm the opening is genuinely active.
3. Check `data/jobs.json` for duplicate URL and company + role combinations.
4. Add a complete job object to `data/jobs.json`.
5. Include accurate verification terms and a browser verification timestamp when manual browser verification was required.
6. Run `python3 generate.py --dry-run`.
7. Run `python3 generate.py`.
8. Verify the homepage card and generated job page.
9. Allow the publishing workflow to re-check availability.
10. Confirm the HD Careers production page is live.
11. Send the job through the correct Telegram path: batch queue or manual/VIP.

Full schema/workflow instructions are in:

```
HOW_TO_ADD_JOB.md
```

## Daily Approval, VIP Publishing and Telegram

The daily 9 AM review flow discovers candidates but currently requires explicit owner review for publication. Discovery V3 remains **shadow-only** and unattended publishing is not enabled.

Admin-approved daily jobs and one-off VIP jobs both need evidence-backed validation, one coordinated generation and website publication, and confirmation that exact production pages are live before Telegram delivery.

The admin publisher uses `data/telegram-approved-batch.json` as its manifest and `scripts/publish_approved_telegram.py` as the automatic sender. Successful Telegram message IDs and uncertain outcomes are recorded in `data/telegram-deliveries.json`. Already-delivered pages are not automatically resent, and uncertain responses require reconciliation.

`publish-verified-telegram.yml` is a **manual maintenance/recovery fallback**, not a second automatic sender. `generate-job-pages.yml` is also manual-only; production generation belongs to the coordinated publication/checker path.

**October 2026 update:** Multi-job approved batches use a receipt-based **hourly Telegram queue**; single VIP jobs can still post immediately once their website pages are verified live. Full lifecycle, timing and recovery rules are documented below.

### Availability and verification uncertainty

The 08:15 and 20:15 IST availability scans remain active. An inconclusive latest check does not automatically expire a previously listed job; instead its generated page and homepage card show **Verification pending**, without renewed `JobPosting` claims. Newer exact-URL owner evidence takes precedence over earlier inconclusive checks. An isolated ATS HTTP 404 or an incomplete Ashby board is not sufficient closure evidence.

`datePosted` is never synthesized from HD Careers' `verifiedDate`. If no usable employer posting date is available, generated `JobPosting` structured data is omitted until truthful original-date provenance can be established.

## Company Logo System

Company logos are resolved and cached by `scripts/resolve_company_logos.py`.

The resolver:

- Prefers official company domains over generic ATS domains
- Prefers SVG/vector and high-resolution official assets
- Supports explicit domain/direct/fallback mappings
- Rejects tiny low-quality raster assets
- Normalizes raster logo padding/canvas quality
- Stores approved assets under `assets/company-icons/`
- Maintains `data/company-logos.json`
- Allows scheduled/manual logo-preview refreshes

This is designed to reduce missing, blurry and incorrect company logos while keeping generated pages fast and stable.

## Deployment

HD Careers production flow:

```
GitHub main
  ↓
GitHub Actions validation / generation
  ↓
Vercel
  ↓
hdcareers.in
```

- Default branch: `main`
- Production domain: `hdcareers.in`
- `www.hdcareers.in` redirects to `hdcareers.in`
- Generated website changes are committed safely back to `main`
- Publishing workflows use concurrency protection and retry when `main` changes during generation
- Vercel build-rate limits can temporarily delay production even when the repository update is already on `main`

## GitHub Actions

Current important workflows:

- `main-data-publish.yml` — verifies changed jobs, resolves logos and generates the website; Telegram delivery requires a separately approved manifest
- `publish-verified-telegram.yml` — manual-only recovery sender using the approval manifest and receipt ledger
- `job-availability.yml` — twice-daily availability/content-quality checks and confirmed closure updates
- `admin-job-generator.yml` — coordinated admin batch publication and automatic receipt-aware Telegram delivery
- `generator-check.yml` — generated-output validation
- `logo-preview-refresh.yml` — company-logo refresh/preview workflow
- `ios-admin-build.yml` — iOS Admin simulator build validation

## Native Android Admin — current v1.3.2

The Android Admin is a native Kotlin / Jetpack Compose / Material 3 app for Pixel devices. The latest privately release-signed build is **v1.3.2, versionCode 8**, produced by Android Admin Private Signed APK workflow. Do not confuse this with a differently signed temporary debug APK. For an existing private release install, use the new signed version for an in-place update; uninstalling erases local login, preferences and notification permissions.

- **Home:** real pending review counts and quick access to expiry exceptions.
- **Review:** daily Priority, Backup, Publish Ready and read-only History; explicitly saved Live/Expired/Unsure decisions, safe one-employer-per-batch publishing and post-publication cleanup.
- **Jobs:** browse existing website records and run approved single VIP publishing through authenticated APIs.
- **More:** job expiry checker, selected new-job publishing, visual GA4 analytics, security/notification controls.
- **Expiry:** only actual unresolved jobs occupy list rows, preventing giant white gaps; confirmable Live, Expired and Unsure buttons. Existing published jobs can be kept/expired but are never re-published from this screen. New Live candidates move to Publish Ready, then require a separate explicit Publish action.
- **Publishing cards:** GitHub, committed data, verified public website page and Telegram receipt are separate stages; expandable cards show due times, queue position, delivery timestamps and links to confirmed messages.
- **Push/local alerts:** FCM integration supports review batches, checker completion, publish workflow outcomes and confirmed hourly Telegram receipts. Notification permission, Firebase/server secrets, connectivity, battery optimization and real-device testing affect delivery. An accepted publish request is NOT proof of completed Telegram delivery.
- **Security:** Android Keystore/optional biometrics plus server-side Admin RBAC; signing keys, tokens and FCM service-account secrets remain private.

Relevant merges: [#109](https://github.com/Chethan-Mns/Hdcareers/pull/109) for expiry list/scroll, Home visibility and notifications; [#110](https://github.com/Chethan-Mns/Hdcareers/pull/110) for History, premium tracking, Live/Expired/Unsure and guarded expiry publishing. The signed APK artifact is available from the [private signed workflow](https://github.com/Chethan-Mns/Hdcareers/actions/workflows/android-admin-private-release.yml), not stored publicly in the repo.

## Native iOS Admin

The repository includes a SwiftUI iOS Admin project under `ios-admin/`.

It is intended to provide mobile access to HD Careers administration, jobs, publishing, checker/review, analytics and related operational views.

The iOS project has its own CI build workflow. Device-runtime changes should still be tested on a real iPhone before risky UI/startup changes are considered production-stable; a successful simulator build proves compilation, not device runtime behavior.

## Analytics

Production tracking uses:

- Google Analytics 4
- Microsoft Clarity
- HD Careers Admin Traffic Analytics

The GA4 admin API is designed to fail softly for optional reports so one unavailable metric does not take down the entire traffic dashboard.

## Supported Categories

```
it
nonit
internship
apprenticeship
campus
remote
walkin
experienced
govt
```

Supported experience types:

```
fresher
experienced
```

## Content Rules

- Prefer exact official employer/recruitment links
- Verify the exact job URL before publishing
- Do not trust a crawler-only closed/fallback page when current browser evidence conflicts with it
- Use original summaries instead of copying large sections from employer pages
- Use `Not Disclosed` when salary is unavailable
- Use `Not Specified` when a fact cannot be verified
- Every published job should have a dedicated HD Careers page
- Keep source and last-verification information
- Mark confirmed closed jobs as `expired`
- Route uncertain jobs to review rather than inventing certainty
- Remove generic/unverified seed records instead of padding the site
- Never invent salary, experience, eligibility, dates, vacancies, fees or company facts
- Keep GitHub and Telegram credentials/tokens server-side
- Prefer quality and employer diversity over simply reaching a numeric batch target

## Current Website TODO

- [ ] Verify on-time delivery of the first autonomous hourly Telegram relay and actual Telegram receipt (do not trust an armed timer alone).
- [ ] Alert on an overdue pending job, failed self-dispatch or unresolved sending/uncertain claims.
- [ ] Test Android v1.3.2 on a real Pixel: Expiry list scrolling, Live/Expired/Unsure, Ready clearing, history and push delivery.
- [ ] If a hard 5–10-minute upper delay bound is required, evaluate a dedicated scheduler; GitHub Actions runner startup is best effort.

- [ ] **Resume score checker:** improve matching visibility, scoring logic and result presentation
- [ ] **Job pages — company section:** add useful source-backed company overview, industry, headquarters, official website and careers information
- [ ] **Analytics cleanup:** combine duplicate homepage paths such as `/` and `/index.html`
- [ ] **Traffic quality:** reduce admin/self-testing traffic where practical
- [ ] **Automation reliability:** continue monitoring queue persistence, verification accuracy and partial-batch behavior
- [ ] **Vercel deployment reliability:** verify/retry production deployments when account build-rate limits interfere
- [ ] **AdSense readiness:** continue improving original content, job-page depth, trust signals and crawlability
- [ ] **Company logos:** continue improving edge cases where an official high-quality logo cannot be resolved
- [ ] **iOS Admin:** complete real-device validation before merging risky startup/UI experiments

### Current Priority Order

1. Job discovery quality and verification accuracy
2. Telegram queue/VIP publishing reliability
3. Resume score checker improvements
4. Company-information section on job pages
5. Analytics and traffic-quality cleanup
6. AdSense readiness
7. iOS Admin real-device stability and UI refinement

## October 2026 Updates — Review, Publishing, Telegram and Reliability

### 1. Owner-controlled daily 20-job review

The daily shortlist targets **10 Priority + 10 Backup** jobs from distinct employers, when enough real verified openings exist. Candidates may be Live, Expired or Unsure. Only Live jobs with the exact verified HTTPS employer URL and complete job content can be selected for publication. The owner may publish **1–10 jobs, one per employer**, rather than padding to ten. Uncertain official-source responses are held for review, not silently expired or published. Discovery V3's unattended automatic publishing remains gated/shadow.

After review, Expired items disappear from the active Priority/Backup list and remain in **History**; an explicitly selected and submitted candidate leaves **Publish Ready** only once its public website page is independently confirmed live. Hiding cards is not deleting job data, audit decisions or Telegram evidence. In-flight hourly Telegram jobs remain trackable.

In the expiry checker, **existing published jobs** are kept active, marked expired or held as Unsure. **New unpublished jobs** verified Live move to a separate Publish Ready section and do not publish automatically. The Publish selected action validates saved Live proof, official URL match, job-content requirements, existing published URLs, the ten-job/unique-employer limit and duplicate dispatch locks. Rejected/newly expired jobs remain archived; Unsure stays pending. RBAC/auth checks remain enforced by API, not only UI.

### 2. Per-job real-time publishing evidence

The redesigned web and Android cards show independent evidence for GitHub workflow execution, repository data commit, Vercel/public page verification, and Telegram actual delivery. The progress panel includes queue position, planned due time, actual sent timestamp and Telegram message IDs where confirmed. A GitHub success alone is not enough to call a job published on the website, and a live page alone is not a Telegram receipt.

Important locations: admin/review-batch.html, admin/index.html, api/admin/publish.js, data/daily-review-batch.json, data/telegram-deliveries.json.

### 3. First Telegram announcement immediately; follow-ups every hour

The publishing path in .github/workflows/admin-job-generator.yml first generates the owner-approved jobs, waits for live production page checks, and posts the **first batch job immediately after website publication**. Single VIP posts retain a separate immediate path after publication.

Multi-job hourly items are durable records in data/telegram-hourly-queue.json; each item progresses through pending, sending, delivered or uncertain states. scripts/hourly_telegram.py computes the next dueAt from the **actual last Telegram delivery time plus 60 minutes**, not from the user's Publish click and not from the previous intended due time.

The .github/workflows/hourly-telegram-queue.yml sender persists an at-most-once claim before sending. It checks public production page availability and saves the Telegram reply's message ID; its separate **wake-next** job uses the saved receipt to wait until the next due time and then dispatches a sender run. The previous five-minute cron remains an emergency backup; a change to data/telegram-scheduler-kick.json can trigger a controlled due-only recovery.

The waiting job does not hold the job-data publishing concurrency lock, and each newly dispatched sender rechecks dueAt and persisted receipts. A state of sending or uncertain must be manually reconciled if the result is ambiguous; do not reset it and blindly retry. **Independent batches have independent timing; cross-batch global spacing is not guaranteed.**

**Timing limitation:** GitHub's schedule, workflow dispatch and hosted runner start are best effort. The target is 60 minutes with a tolerable small delay, but a 5–10-minute maximum is **not guaranteed**. The operator must verify a concrete Telegram delivery message ID before claiming success; use dedicated managed scheduling if strict timing becomes necessary. The self-waking GitHub runner also consumes Actions runner time while sleeping.

### 4. Incident and fix on 18 October 2026 (historical example)

Accenture was delivered at **12:52:49 PM IST**, message [#520](https://t.me/HD_Careers/520). The next AiPrise message was due at **1:52:49 PM IST**, but a missed GitHub scheduled wake-up left it pending. Controlled due-only recovery confirmed AiPrise at **3:14:44 PM IST** as [#521](https://t.me/HD_Careers/521). The next planned Bosch target was **4:14:44 PM IST**. This is a historical due-time snapshot, not proof of Bosch delivery; the queue/ledger must be checked live.

The repair merged as [PR #111](https://github.com/Chethan-Mns/Hdcareers/pull/111) and was activated: the new wake-next job was observed running and waiting for the actual saved Bosch dueAt. Existing confirmed posts were not duplicated.

### 5. Safely investigating a missed Telegram post

1. Read the **latest** data/telegram-hourly-queue.json and data/telegram-deliveries.json from main; check last confirmed messageId/deliveredAt, next dueAt, and any uncertain/sending state.
2. Inspect [GitHub Actions](https://github.com/Chethan-Mns/Hdcareers/actions), especially Hourly Telegram Job Announcements and its send-one and wake-next jobs, plus Admin Direct Publish.
3. If dueAt has passed but the queue remains pending, determine whether wake-next failed dispatch, GitHub runner startup was delayed, or cron failed to fire.
4. For a **confirmed pending** overdue record only, trigger a controlled scheduler kick rather than sending it directly. Confirm the next workflow claims just one due job and reconciles receipts.
5. If a record says sending/uncertain, inspect the Telegram channel and workflow artifact **before any retry**. Prevent duplicated channel posts.
6. Confirm the actual Telegram receipt and new next-due calculation. Update owner-facing history if an exception remains.

### 6. Other recently shipped changes

| PR | Key changes |
| --- | --- |
| [#105](https://github.com/Chethan-Mns/Hdcareers/pull/105) | Job-by-job GitHub, website, queue and Telegram progress tracking |
| [#106](https://github.com/Chethan-Mns/Hdcareers/pull/106) | Content quality, AdSense-readiness and SEO/crawlability improvements; AdSense approval is not implied |
| [#107](https://github.com/Chethan-Mns/Hdcareers/pull/107) and [#108](https://github.com/Chethan-Mns/Hdcareers/pull/108) | Hourly queued delivery, safe claims, due tracking and controlled scheduler kickoff |
| [#109](https://github.com/Chethan-Mns/Hdcareers/pull/109) | Android expiry list/scroll fixes, interactive controls, Home reviews and push events |
| [#110](https://github.com/Chethan-Mns/Hdcareers/pull/110) | Web + Android History, separate expiry Publish Ready, guarded publish and premium timelines, APK v1.3.2 |
| [#111](https://github.com/Chethan-Mns/Hdcareers/pull/111) | Receipt-timed self-waking hourly dispatch + cron fallback and regression tests |

Additional workflow regression coverage includes tests/test_hourly_telegram_queue.py, tests/review-lifecycle-ui.test.mjs and tests/android-push-config.test.mjs. The iOS Admin remains a separate simulator-tested prototype. GA4, Clarity, company-logo resolution, job page SEO, audit controls, privacy/trust pages and AdSense content improvements continue to be maintained.

---

## Project Recovery / New Chat

The broader project context is stored in:

```
PROJECT_CONTEXT.md
```

If previous ChatGPT context is unavailable, start a new chat and say:

> Open the GitHub repository `Chethan-Mns/Hdcareers`, read `README.md` and `PROJECT_CONTEXT.md`, inspect the current `main` branch, and continue from the current repository state.

Repository state is authoritative when documentation and an old conversation disagree.

## Contact

- Email: helpdeskinreallife@gmail.com
- Telegram: https://t.me/HD_Careers
- Instagram: https://instagram.com/hd_careers

## Security

Admin tooling must keep GitHub credentials, Telegram bot tokens, analytics credentials and other secrets server-side. Never expose secrets in public JavaScript, generated job pages, repository documentation or client-side application bundles.
