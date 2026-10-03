# HD Careers Project Context

## Project
HD Careers is a static jobs and careers website deployed from GitHub to Vercel.

- Repository: Chethan-Mns/Hdcareers
- Production domain: https://hdcareers.in
- Canonical domain: hdcareers.in
- www redirects to hdcareers.in
- Hosting: Vercel
- Default branch: main

## Current Site Structure

```
README.md
assets/
data/
  jobs.json
generate.py
index.html
jobs/
.github/
  workflows/
    generator-check.yml
```

## Job Publishing Architecture

`data/jobs.json` is the single source of truth for jobs.

Each job entry contains:
- id
- page
- domain
- company
- salary
- logo
- role
- roleTag
- loc
- locationFilter
- batch
- elig
- cat
- expType
- expYears
- date
- desc
- resp
- apply

The generator is:

```
python3 generate.py
```

It updates:
- homepage job data inside index.html
- individual job pages under jobs/

Safe validation command:

```
python3 generate.py --dry-run
```

## Publishing Workflow

Always use this flow:

1. Verify the official job posting.
2. Create a new branch from main.
3. Add/update the job in data/jobs.json.
4. Run generate.py.
5. Verify index.html and the generated job page.
6. Commit changes.
7. Create a pull request to main.
8. Check the Vercel Preview deployment.
9. Merge only after verification.
10. Confirm production deployment succeeds.

Do not edit main directly for normal changes.

## Homepage Behavior

The current homepage:
- Uses V8 styling.
- Has search, categories, level, experience, role, company and location filters.
- Removes the large four-card WhatsApp/Instagram/Telegram strip from the main content.
- Keeps social links in the header/mobile menu/sidebar/footer.
- Scrolls users to the results section when categories, sort, level or search/filter inputs change.
- Text input filters use a short debounce before scrolling to avoid excessive jumping.

## Job Page Design

Individual job pages use the current HD Careers job-page style and include:
- Hero with company, role, location, batch, posted date and salary/stipend.
- Job overview.
- Eligibility.
- Responsibilities.
- How to apply.
- Official Apply link.
- Disclaimer.
- Share button that shares the HD Careers job URL.
- WhatsApp/social follow section.

Do not replace the current visual style unless explicitly requested.

## Content Rules

- Prefer official company career links.
- Verify job details before publishing.
- Rewrite job descriptions in clear original wording; do not copy large blocks verbatim.
- If salary is not stated, use "Not Disclosed".
- If batch is not stated, use "Not Specified".
- Keep location and experience filters practical and searchable.
- Every job should have a dedicated HD Careers page before publishing.

## Categories

Supported category values:

- it
- internship
- apprenticeship
- campus
- remote
- walkin
- experienced
- govt

Supported experience types:

- fresher
- experienced

## Social / Contact

- Contact email: helpdeskinreallife@gmail.com
- Telegram: https://t.me/HD_Careers
- Instagram: https://instagram.com/hd_careers

WhatsApp links already exist in the site. Preserve current working links unless explicitly asked to change them.

## Deployment Safety

Before merging:
- Ensure the PR only contains intended files.
- Ensure Vercel Preview is Ready.
- Ensure generated job pages load.
- Ensure homepage search and filters still work.
- Ensure official apply links open the intended source.
- Keep production changes behind a PR whenever possible.

## Future Admin Tool

A future /admin tool is planned.

Desired flow:

```
Admin login
  ↓
Add Job form
  ↓
Preview
  ↓
Publish
  ↓
Update jobs.json
  ↓
Run generator
  ↓
Commit/PR/deploy
```

The admin tool should never expose GitHub tokens in client-side HTML. Any GitHub write access should go through a protected backend/serverless API using environment variables.

## Fresh Chat Recovery

If this ChatGPT conversation is unavailable, start a new chat and say:

"Open the GitHub repository Chethan-Mns/Hdcareers and read PROJECT_CONTEXT.md. Continue working from that file and the current repository state."

Then inspect the current branch and latest files before making changes.

<!-- Vercel deployment retry: 2026-10-03 16:29 IST -->
