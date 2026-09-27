# HD Careers Admin V1 Setup

The first admin version is available at:

```
/admin/
```

## What V1 does

- Accepts an official job URL.
- Calls a protected server-side extraction endpoint.
- Tries to read JobPosting JSON-LD / page metadata.
- Fills the job form automatically.
- Lets the admin edit every generated field.
- Supports fully manual entry.
- Shows a homepage-card preview.
- Generates a `jobs.json` object for review.

V1 intentionally does **not** publish to GitHub yet.

## Required Vercel Environment Variable

Add:

```
ADMIN_EXTRACT_KEY=<a long random secret>
```

Use a long unique value. This is only for the extraction endpoint and is not a GitHub token.

Add it in Vercel:

```
Project Settings
→ Environment Variables
→ ADMIN_EXTRACT_KEY
```

Apply it to Preview and Production as needed, then redeploy.

## Security

The extraction API:

- Requires the admin key.
- Only accepts HTTPS URLs.
- Rejects localhost/private network addresses.
- Resolves DNS and blocks private IP ranges.
- Limits redirects.
- Limits page size.
- Uses a request timeout.
- Does not contain or expose a GitHub token.

The browser keeps the extraction key in `sessionStorage`, so it is cleared when the browser session/tab is closed.

## Automatic extraction limitations

Different companies structure career pages differently.

Pages with Schema.org `JobPosting` JSON-LD usually extract best.

Always review:

- company
- role
- location
- experience
- salary
- eligibility
- description
- responsibilities
- official apply URL

before publishing.

## Next version

After V1 UI/extraction is approved:

```
Reviewed form
→ protected publish API
→ branch
→ update data/jobs.json
→ generate pages
→ PR
→ Vercel Preview
→ merge
```

GitHub credentials must remain server-side in Vercel environment variables.
