# HD Careers (hdcareers.in)

HD Careers is a mobile-first jobs and careers website for India, built with HTML, Tailwind CSS (CDN), vanilla JavaScript, and a lightweight Python generator.

Production: https://hdcareers.in

## Current Architecture

```
README.md
PROJECT_CONTEXT.md
HOW_TO_ADD_JOB.md
assets/
data/
  jobs.json
  job-template.json
generate.py
index.html
jobs/
.github/
  workflows/
    generator-check.yml
```

## Features

- Latest jobs, internships, apprenticeships, off-campus drives, remote roles, walk-ins, experienced jobs and government jobs
- Search by role, company, skill and related job information
- Filters for category, level, experience, role, company and location
- Automatic scroll to updated job results after search/filter changes
- Separate SEO-friendly job pages under `/jobs/`
- Official company application links
- Job sharing using HD Careers job-page URLs
- Responsive mobile-first UI
- WhatsApp, Instagram and Telegram links
- Crawlable About, Contact, Privacy Policy, Terms and Disclaimer pages
- Vercel Preview deployments before production merges
- Generator validation workflow through GitHub Actions

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

1. Verify the official company job posting.
2. Create a new branch from `main`.
3. Add the job to `data/jobs.json`.
4. Run `python3 generate.py --dry-run`.
5. Run `python3 generate.py`.
6. Verify the homepage card and generated job page.
7. Commit the changes.
8. Open a pull request to `main`.
9. Check the Vercel Preview deployment.
10. Merge only after verification.

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
- Vercel automatically creates preview deployments for pull requests

## Supported Categories

```
it
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
- Verify job details before publishing
- Use original summaries instead of copying large sections from company pages
- Use `Not Disclosed` when salary is not provided
- Use `Not Specified` when batch information is unavailable
- Every published job should have a dedicated HD Careers job page
- Keep a source name and last-verified date for every job
- Mark closed jobs as `expired` instead of continuing to present them as active
- Remove generic/unverified seed records rather than padding the site with thin content
- Keep normal production changes behind a branch + pull request

## Contact

- Email: helpdeskinreallife@gmail.com
- Telegram: https://t.me/HD_Careers
- Instagram: https://instagram.com/hd_careers

## Future Plan

A protected `/admin` tool is available for reviewing and publishing verified jobs without exposing GitHub credentials to the browser.

The intended flow is:

```
Admin Login
  ↓
Add Job
  ↓
Preview
  ↓
Publish
  ↓
Update jobs.json
  ↓
Run generator
  ↓
Deploy
```

Any future admin tool must keep GitHub credentials or tokens on the server side and never expose them in client-side code.
