# HD Careers (hdcareers.in)

HD Careers is a mobile-first jobs and careers platform for India, built with HTML, Tailwind CSS (CDN), vanilla JavaScript, a lightweight Python generator, GitHub Actions, Vercel, and an admin/iOS workflow for publishing and monitoring jobs.

Production: https://hdcareers.in

## Current Architecture

```
README.md
PROJECT_CONTEXT.md
HOW_TO_ADD_JOB.md
assets/
  analytics.js
data/
  jobs.json
  job-template.json
  automation-status.json
generate.py
index.html
jobs/
admin/
  index.html
  traffic.html
  ios-preview.html
ios-admin/
api/
.github/
  workflows/
    admin-job-generator.yml
    generator-check.yml
    ios-admin-build.yml
    job-availability.yml
    main-data-publish.yml
```

## Features

- Latest jobs, internships, apprenticeships, off-campus drives, remote roles, walk-ins, experienced jobs, government jobs and non-IT jobs
- Search by role, company, skill and related job information
- Filters for category, level, experience, role, company and location
- Automatic scroll to updated job results after search/filter changes
- Separate SEO-friendly job pages under `/jobs/`
- Official company application links
- Dynamic company logos with fallbacks
- Job sharing using HD Careers job-page URLs
- Responsive mobile-first UI with separate desktop layout tuning
- WhatsApp, Instagram and Telegram links
- Resume-to-JD matching / score checker
- Protected admin dashboard for publishing and maintenance
- Traffic analytics page backed by Google Analytics 4
- Microsoft Clarity tracking
- Automatic expired-job availability checks
- Scheduled HD Careers job publishing automations
- Telegram auto-posting after publish
- Native iOS Admin app project
- Crawlable About, Contact, Privacy Policy, Terms and Disclaimer pages
- GitHub Actions validation and generation workflows

## Current Website TODO

This section is the working TODO list for the HD Careers website.

- [ ] **Desktop UI:** deploy and verify the approved desktop layout with balanced left/right spacing without changing the mobile UI
- [ ] **Resume score checker:** improve the resume/JD matching experience, visibility, scoring logic and result presentation
- [ ] **Job pages — company section:** research and add useful company information such as company overview, industry, headquarters, official website, careers page and other source-backed details
- [ ] **Analytics cleanup:** combine duplicate homepage paths such as `/` and `/index.html` in traffic reporting
- [ ] **Traffic quality:** exclude or reduce admin/self-testing traffic where practical
- [ ] **Automation health:** ensure every scheduled slot records `published`, `no_publish` or `error` and notifies the admin
- [ ] **Vercel deployment reliability:** retry/verify pending production deployments when the build-rate limit clears
- [ ] **AdSense readiness:** continue improving useful original content, job-page depth, trust signals and crawlability
- [ ] **Company logos:** continue improving missing, blurry or incorrect company logos dynamically

### Current Priority Order

1. Desktop UI production verification
2. Resume score checker improvements
3. Company-information section on job pages
4. Analytics cleanup and traffic-quality improvements
5. Automation/deployment reliability

## Job Data

`data/jobs.json` is the single source of truth for job listings.

Do not manually maintain duplicate job content in multiple places.

A reusable sample object is available at:

```
data/job-template.json
```

## Generate the Site

Preview what would change:

```bash
python3 generate.py --dry-run
```

Generate/update the homepage job data and individual job pages:

```bash
python3 generate.py
```

The generator updates:

- Active job data inside `index.html`
- Individual verified pages under `jobs/`
- `robots.txt`
- `sitemap.xml`

## Add a New Job

Recommended workflow:

1. Verify the exact official company job posting is live.
2. Check `data/jobs.json` for duplicates.
3. Add a complete job object to `data/jobs.json`.
4. Run `python3 generate.py --dry-run`.
5. Run `python3 generate.py`.
6. Verify the homepage card and generated job page.
7. Commit the changes.
8. Allow the publishing workflow to validate availability.
9. Confirm the production deployment.
10. Confirm Telegram posting when applicable.

Full instructions:

```
HOW_TO_ADD_JOB.md
```

## Deployment

HD Careers is deployed through:

```
GitHub
  ↓
Vercel
  ↓
hdcareers.in
```

- Default branch: `main`
- Production domain: `hdcareers.in`
- `www.hdcareers.in` redirects to `hdcareers.in`
- Production deploys are triggered from repository updates
- Vercel build-rate limits can temporarily delay deployment even when code is already merged to `main`

## Automation Schedule

The active HD Careers publishing slots are:

- 9:00 AM — Fresher IT
- 12:00 PM — Fresher Non-IT
- 3:00 PM — Experienced IT
- 6:00 PM — Government / PSU
- 9:00 PM — Walk-in

Each automation should verify the exact official job source before publishing and update `data/automation-status.json` with its final outcome.

## Analytics

Production tracking currently uses:

- Google Analytics 4
- Microsoft Clarity
- HD Careers Admin Traffic Analytics

The traffic dashboard includes:

- Live users
- Unique visitors
- Page views
- Views per visitor
- Top pages
- Traffic sources
- Countries
- Devices

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

## Project Recovery / New Chat

The full project context is stored in:

```
PROJECT_CONTEXT.md
```

If the previous ChatGPT conversation is unavailable, start a new chat and say:

> Open the GitHub repository `Chethan-Mns/Hdcareers` and read `PROJECT_CONTEXT.md`. Continue working from that file and the current repository state.

This keeps the project workflow independent of any single chat.

## Content Rules

- Prefer official company career links
- Verify the exact job URL is active before publishing
- Use original summaries instead of copying large sections from company pages
- Use `Not Disclosed` when salary is not provided
- Use `Not Specified` when information is unavailable
- Every published job should have a dedicated HD Careers job page
- Keep a source name and last-verified date for every job
- Mark closed jobs as `expired` instead of continuing to present them as active
- Remove generic/unverified seed records rather than padding the site with thin content
- Keep GitHub credentials and tokens server-side
- Avoid inventing salary, experience, eligibility, dates or company facts

## Contact

- Email: helpdeskinreallife@gmail.com
- Telegram: https://t.me/HD_Careers
- Instagram: https://instagram.com/hd_careers

## Admin Publishing Flow

```
Admin Login
  ↓
Add / Extract Job
  ↓
Review
  ↓
Preview
  ↓
Publish
  ↓
Update jobs.json
  ↓
Verify availability
  ↓
Run generator
  ↓
Deploy
  ↓
Post to Telegram
```

Any admin tooling must keep GitHub credentials or tokens on the server side and never expose them in client-side code.
