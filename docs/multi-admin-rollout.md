# HD Careers multi-admin rollout (Owner + Job Editor)

## Status

Shadow development branch: `feature/multi-admin-rbac`. This feature is NOT merged into `main`.
All job-publishing workflows and existing Owner Vercel credentials remain unchanged.
The preview deployment is explicitly read-only for production job mutations.

## Required Vercel configuration

In **Vercel → hdcareers → Settings → Environment Variables**, add:

| Name | Environment | Value |
| --- | --- | --- |
| `HD_ADMIN_REDIS_URL` | Preview | HTTPS REST URL of a dedicated test Upstash Redis instance |
| `HD_ADMIN_REDIS_TOKEN` | Preview | REST token for the above instance |
| `HD_ADMIN_REDIS_URL` | Production, after approval | HTTPS REST URL of a dedicated production Upstash Redis instance |
| `HD_ADMIN_REDIS_TOKEN` | Production, after approval | REST token for the production instance |

Use different Redis databases/instances for Preview and Production. Mark tokens sensitive and never commit tokens,
user passwords or bearer sessions to GitHub.

Keep these existing Owner variables in both environments without changing their values:

- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `ADMIN_SESSION_SECRET`

`ADMIN_PASSWORD_HASH` is legacy and is not used by this change. Keep the original Owner variables intact.

## Testing without affecting the website

1. Configure **Preview** Redis REST variables only and redeploy `feature/multi-admin-rbac`.
2. Open the branch's Vercel preview URL (may require existing Vercel preview SSO).
3. Sign in as Owner at `/admin/` using your **existing** Owner username/password.
4. Select **Team** or open `/admin/team.html`. Create a Job Editor with a unique username and a password of 14+ characters.
5. Open the preview in a separate private browser session and sign in as the Job Editor.
6. Verify Editor can view/manage job workflows but cannot access `/api/admin/team`, `/api/admin/audit`, `/api/admin/traffic` or the traffic page. Job-write requests on Preview are blocked.
7. While the Editor is logged in, as Owner click **Sign out all devices** and confirm the Editor's next request is rejected.
8. Disable the Editor and confirm they cannot log in. Re-enable, reset the password and confirm old passwords fail.
9. Review audit events at `/admin/team.html`.
10. Only after preview tests pass and the Owner explicitly approves merging, configure Production Redis and promote.

The earlier signed admin sessions are intentionally invalidated by migration. Re-login with the same Owner credentials.

## Role matrix

| Feature | Owner | Job Editor |
| --- | :---: | :---: |
| Login, manage job listing, extract job data | Yes | Yes |
| Approve/review jobs, publish selected jobs, daily review batch | Yes | Yes |
| View availability status and review queue | Yes | Yes |
| Trigger global expired-job checker | Yes | No |
| GA4/traffic private analytics | Yes | No |
| Create/disable/reset editors; revoke sessions | Yes | No |
| View audit log | Yes | No |

Enforcement is server-side for every admin API; hiding a UI button is never used as the authorization boundary.

## Security behavior

- Per-editor credentials are hashed using per-user salt and Node `scrypt` before writing to the Redis-backed store.
- Owner password continues to be checked against existing Vercel Owner credentials.
- Sessions are opaque 256-bit tokens stored server-side as HMAC-derived keys, with a maximum life of 12 hours.
- Sessions use `HttpOnly; Secure; SameSite=Strict` cookies; iOS/Bearer login continues to be supported.
- Logout deletes the session. Disable/password reset/sign-out-all changes a user revision and immediately invalidates all their existing sessions.
- Owner account cannot be modified by the team-management endpoint.
- Login attempts are limited using persistent Redis counters. A store outage fails closed rather than granting access.
- Audit records actor, role, action, target and timestamp (without passwords), retaining up to 1000 events.
- GitHub job mutations are audit-logged before execution. An audit-store outage blocks the mutation.
- Preview job-publishing, review changes and checker-trigger calls are read-only by design.

## Limitations / next production considerations

- A third-party Redis/Upstash account is required; Vercel environment variables alone do not store revocable sessions.
- GitHub writes and Redis audits are separate systems; audit records represent requests/attempts and are not a transactional ledger of final GitHub commits.
- Rate limiting applies per username and client IP; consider additional Vercel WAF limits for high-risk public admin endpoints.
- A production deployment must not occur before production secrets and a successful preview sign-in test are available.
