# HD Careers (hdcareers.in)

HD Careers is a mobile-first jobs and careers platform for India. It combines a static public website, Python-based job generation and verification, GitHub Actions automation, Vercel production hosting, GA4/Clarity analytics, Telegram distribution, a protected web admin, and a native iOS Admin project.

Production: https://hdcareers.in

_Last refreshed: 06 Oct 2026_

## Current Architecture

```
README.md
PROJECT_CONTEXT.md
HOW_TO_ADD_JOB.md

assets/
  analytics.js
  editorial.css
  public-header.css
  public-header.js
  company-icons/

data/
  jobs.json
  job-template.json
  automation-status.json
  availability-status.json
  review-queue.json
  telegram-queue.json
  company-logos.json
  company-logo-domains.json
  company-logo-direct.json
  company-logo-quality-fallbacks.json

scripts/
  admin_publish.py
  check_job_availability.py
  check_content_quality.py
  resolve_company_logos.py
  post_telegram.py
  post_telegram_from_push.py
  telegram_queue.py

generate.py
index.html
jobs/
insights.html
insights/

admin/
  index.html
  traffic.html
  ios-preview.html

api/
  admin/
    availability.js
    review.js
    traffic.js

ios-admin/

.github/
  workflows/
    admin-job-generator.yml
    generator-check.yml
    hourly-telegram-publish.yml
    ios-admin-build.yml
    job-availability.yml
    logo-preview-refresh.yml
    main-data-publish.yml
```

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
- `data/telegram-queue.json` — persistent hourly Telegram queue and posting history
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

## Two Publishing Paths

HD Careers deliberately keeps automated batch publishing and manually supplied jobs separate.

### 1. Daily Batch

The 9 AM automation discovers a broad candidate pool before selecting the final batch.

Current selection policy:

- Aim for about 10 strong verified jobs
- Prioritize at least 5 useful fresher/early-career IT or technical opportunities
- Prefer new-grad, graduate, apprentice, internship, trainee, Software Engineer I and 0–2 YOE roles
- Search broadly across MNCs, product companies, Big Four firms, startups and official government/public-sector sources
- Build a substantially larger candidate pool before selecting the final jobs
- Target 8–10 different employers in a 10-job batch
- Normally select only one job per employer
- Never select more than two jobs from one employer
- Prefer recent roles and direct official application pages
- Do not publish weak/repetitive roles merely to fill a quota

The batch updates `data/jobs.json` once, re-verifies the selected jobs, generates/deploys the surviving pages, and then persists those jobs to `data/telegram-queue.json`.

A failed or unverifiable listing must not block the rest of a valid batch.

### 2. Manual / VIP Job

A job explicitly supplied for immediate publishing uses a commit beginning with:

```
Manual publish:
```

The flow is:

```
Verify official job
  ↓
Update jobs.json
  ↓
Re-check availability
  ↓
Generate HD Careers page
  ↓
Deploy / confirm page is live
  ↓
Post to Telegram immediately
```

A manual/VIP job does **not** join, replace, reorder, pause or consume the normal hourly batch queue.

The VIP publisher also supports retrying a manually updated job through `manualPublishRequestedAt` without confusing it with a brand-new batch listing.

## Telegram Queue

Batch Telegram publishing is persistent and stateful.

`data/telegram-queue.json` contains:

- `pending` — jobs waiting for an hourly slot
- `posted` — posting history and timestamps

`scripts/telegram_queue.py` supports:

```
enqueue <before-sha>
publish-one
publish-new <before-sha>
```

The hourly workflow runs at:

```
10:00 AM through 8:00 PM IST
```

Each scheduled run posts at most one publishable queued job. For a normal 10-job batch starting at 10 AM, the expected slots are 10 AM through 7 PM. An 11th pending item can use the 8 PM slot.

Queue state is committed back to `main`, so pending jobs survive unrelated website changes. Manual/VIP Telegram posts are independent of this queue.

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

- `main-data-publish.yml` — verifies new jobs, resolves logos, generates/deploys the site, queues batch jobs, and immediately posts manual/VIP jobs after deployment
- `hourly-telegram-publish.yml` — posts one pending Telegram batch job per hourly slot
- `job-availability.yml` — twice-daily availability/content-quality checks and confirmed closure updates
- `admin-job-generator.yml` — admin publishing support
- `generator-check.yml` — generated-output validation
- `logo-preview-refresh.yml` — company-logo refresh/preview workflow
- `ios-admin-build.yml` — iOS Admin simulator build validation

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
