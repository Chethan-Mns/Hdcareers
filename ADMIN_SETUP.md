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

Admin authentication now uses a normal username + password login.

Required variables:

```
ADMIN_USERNAME=<your chosen username>
ADMIN_PASSWORD_HASH=<scrypt password hash>
ADMIN_SESSION_SECRET=<long random session secret>
```

The old `ADMIN_EXTRACT_KEY` is no longer used for admin login.

Generate a password hash locally on your Mac:

```bash
node -e "const crypto=require('crypto');const p=process.argv[1];const s=crypto.randomBytes(16);const h=crypto.scryptSync(p,s,64);console.log('scrypt
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


## Direct production publishing

The admin now uses this flow:

```
Deploy Live
→ authenticated serverless publish API
→ GitHub repository_dispatch
→ GitHub Actions validates selected jobs
→ update data/jobs.json
→ run generate.py
→ commit jobs.json + homepage + generated job pages together to main
→ Vercel production deployment
```

There is no publishing PR in this mode because the admin already provides editable card/full-page previews before deployment.

### Required Vercel variable

```
GITHUB_PUBLISH_TOKEN=<GitHub fine-grained token>
```

Repository access should be limited to `Chethan-Mns/Hdcareers`.

Permissions required:

- Contents: Read and write
- Metadata: Read-only

Pull requests permission is no longer required for direct publishing, but leaving it enabled is harmless.

The token stays server-side in Vercel and is never included in the admin HTML or browser response.

### Safety

Direct publishing still validates required fields and duplicate URLs/company-role pairs. The GitHub workflow runs `generate.py` and `git diff --check` before it commits to `main`. If validation fails, nothing is pushed to production.
+s.toString('hex')+'
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


## Direct production publishing

The admin now uses this flow:

```
Deploy Live
→ authenticated serverless publish API
→ GitHub repository_dispatch
→ GitHub Actions validates selected jobs
→ update data/jobs.json
→ run generate.py
→ commit jobs.json + homepage + generated job pages together to main
→ Vercel production deployment
```

There is no publishing PR in this mode because the admin already provides editable card/full-page previews before deployment.

### Required Vercel variable

```
GITHUB_PUBLISH_TOKEN=<GitHub fine-grained token>
```

Repository access should be limited to `Chethan-Mns/Hdcareers`.

Permissions required:

- Contents: Read and write
- Metadata: Read-only

Pull requests permission is no longer required for direct publishing, but leaving it enabled is harmless.

The token stays server-side in Vercel and is never included in the admin HTML or browser response.

### Safety

Direct publishing still validates required fields and duplicate URLs/company-role pairs. The GitHub workflow runs `generate.py` and `git diff --check` before it commits to `main`. If validation fails, nothing is pushed to production.
+h.toString('hex'))" 'YOUR_PASSWORD'
```

Generate the session secret separately:

```bash
openssl rand -base64 48
```

Set all three variables for Preview and Production, then redeploy. Do not commit or share these values.

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


## Direct production publishing

The admin now uses this flow:

```
Deploy Live
→ authenticated serverless publish API
→ GitHub repository_dispatch
→ GitHub Actions validates selected jobs
→ update data/jobs.json
→ run generate.py
→ commit jobs.json + homepage + generated job pages together to main
→ Vercel production deployment
```

There is no publishing PR in this mode because the admin already provides editable card/full-page previews before deployment.

### Required Vercel variable

```
GITHUB_PUBLISH_TOKEN=<GitHub fine-grained token>
```

Repository access should be limited to `Chethan-Mns/Hdcareers`.

Permissions required:

- Contents: Read and write
- Metadata: Read-only

Pull requests permission is no longer required for direct publishing, but leaving it enabled is harmless.

The token stays server-side in Vercel and is never included in the admin HTML or browser response.

### Safety

Direct publishing still validates required fields and duplicate URLs/company-role pairs. The GitHub workflow runs `generate.py` and `git diff --check` before it commits to `main`. If validation fails, nothing is pushed to production.
