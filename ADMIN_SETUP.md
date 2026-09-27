# HD Careers Admin V1 Setup

The admin is available at `/admin/`.

## Current V1 features

- Secure password login.
- HttpOnly signed admin session cookie.
- Multiple official job links per batch.
- Up to 20 links per batch, processed three at a time.
- Server-side job extraction.
- Duplicate detection.
- Editable/manual jobs.
- Full-page desktop/mobile previews.

GitHub publishing is intentionally not connected yet.

## Vercel environment variables

Your existing:

```
ADMIN_EXTRACT_KEY=<your strong secret>
```

can be used as the admin login password for V1.

Recommended: also add an independent session-signing secret:

```
ADMIN_SESSION_SECRET=<another long random secret>
```

Generate it locally with:

```bash
openssl rand -base64 48
```

Set both for Preview and Production, then redeploy.

## Authentication flow

```
/admin/
→ password login
→ /api/admin/login
→ signed HttpOnly + Secure + SameSite=Strict cookie
→ admin dashboard
```

API routes:

```
/api/admin/login
/api/admin/session
/api/admin/logout
/api/admin/extract-job
```

The extraction endpoint now requires the authenticated session instead of exposing the extraction secret in browser requests.

Sessions expire after 12 hours. Repeated failed logins get a temporary in-memory lockout.

## Next version

```
Reviewed jobs
→ protected publish API
→ GitHub branch
→ update data/jobs.json
→ run generator
→ PR
→ Vercel Preview
→ merge
```


## GitHub publishing setup

The admin now supports:

```
Deploy Selected
→ authenticated serverless publish API
→ new GitHub branch
→ update data/jobs.json
→ open pull request
→ GitHub Actions runs generate.py
→ Vercel creates a PR preview
→ review
→ merge to main
```

### Required Vercel variable

Create a fine-grained GitHub personal access token and save it only in Vercel:

```
GITHUB_PUBLISH_TOKEN=<GitHub token>
```

Recommended token scope:

- Repository access: only `Chethan-Mns/Hdcareers`
- Contents: Read and write
- Pull requests: Read and write
- Metadata: Read-only

Set the variable for Preview and Production.

Optional repository/base overrides:

```
ADMIN_GITHUB_REPO=Chethan-Mns/Hdcareers
ADMIN_GITHUB_BASE=main
```

The GitHub token must never be added to client-side HTML or committed to the repository.
