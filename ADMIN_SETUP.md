# HD Careers Admin Setup

The admin is available at:

```
/admin/
```

## Admin authentication

The admin uses a normal username and password, verified only on the server.

Required Vercel environment variables:

```
ADMIN_USERNAME=<your chosen username>
ADMIN_PASSWORD=<your normal password>
ADMIN_SESSION_SECRET=<long random random value>
```

Set all three for:

- Production
- Preview

Use Vercel **Secret** variables for `ADMIN_PASSWORD` and `ADMIN_SESSION_SECRET`.

The login password is never committed to GitHub and is never embedded in the admin HTML or client-side JavaScript.

The older `ADMIN_PASSWORD_HASH` and `ADMIN_EXTRACT_KEY` values are not used by the current login flow.

## Authentication flow

```
/admin/
→ username + password
→ /api/admin/login
→ server verifies Vercel secrets
→ signed HttpOnly + Secure + SameSite=Strict cookie
→ admin dashboard
```

Sessions expire after 12 hours. Repeated failed logins receive a temporary in-memory lockout.

Admin API routes:

```
/api/admin/login
/api/admin/session
/api/admin/logout
/api/admin/extract-job
/api/admin/publish
```

## Job intake

The admin supports:

- single or multiple official job links
- up to 20 links per batch
- server-side extraction
- duplicate detection
- editable/manual jobs
- full-page desktop/mobile previews

## Direct production publishing

The current publishing flow is:

```
Deploy Live
→ authenticated /api/admin/publish
→ GitHub repository_dispatch
→ GitHub Actions validates selected jobs
→ update data/jobs.json
→ run generate.py
→ commit jobs.json + homepage + generated job pages to main
→ Vercel production deployment
```

Required Vercel variable:

```
GITHUB_PUBLISH_TOKEN=<GitHub fine-grained token>
```

Recommended repository access:

- only `Chethan-Mns/Hdcareers`
- Contents: Read and write
- Metadata: Read-only

The GitHub token remains server-side.

## Safety

Direct publishing validates required fields and duplicate URLs/company-role pairs. The GitHub workflow runs `generate.py` and `git diff --check` before committing to `main`. If validation fails, nothing is pushed to production.
