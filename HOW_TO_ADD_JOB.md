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
