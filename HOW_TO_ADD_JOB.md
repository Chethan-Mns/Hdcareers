# How to Add a Job to HD Careers

## Recommended Method

Use a separate branch for each new job.

Example:

```
add-company-role
```

## Steps

1. Verify the official job link and job details.

2. Open:

```
data/jobs.json
```

3. Copy the template from:

```
data/job-template.json
```

4. Add the new job object near the top of the jobs array.

5. Use the next available numeric id.

6. Set a unique page path:

```
jobs/company-role.html
```

7. Put the official application URL in:

```
"apply": "https://..."
```

8. Run:

```
python3 generate.py --dry-run
```

9. If the dry run looks correct, run:

```
python3 generate.py
```

10. Verify:
- index.html includes the new job
- the new jobs/<slug>.html file exists
- company, role, location, eligibility and official apply link are correct

11. Commit the changed files.

12. Create a pull request to main.

13. Wait for Vercel Preview.

14. Open the preview and check:
- homepage card
- filter/search behavior
- individual job page
- Official Apply button
- mobile layout

15. Merge after verification.

## Notes

- Do not publish unverified third-party links when an official company page is available.
- Do not manually maintain duplicate job data in multiple places. data/jobs.json is the source of truth.
- If salary or batch is not stated, use "Not Disclosed" or "Not Specified".
- If a job no longer exists, verify before removing it.
