# HD Careers Job Radar V3 — Shadow prototype

This branch is **shadow-only**. It does not write `data/jobs.json`, alter public pages,
call Vercel deployment APIs or send Telegram messages.

## Implemented

- First-class public ATS inventory discovery (Greenhouse, Lever, Ashby)
- Exact provider/tenant/requisition identity keys, deduplication and structured records
- Durable JSON snapshot history across runs
- Detect missing requisitions only after successful complete inventory scans
- Reject blocked/error responses and suspicious inventory collapses
- Do not equate HTTP 403/404, disappearance or stale generic Apply text with expiry
- Recheck missing jobs without automatically expiring them
- Require exact Tier-A open verifier evidence **and** a recent current inventory before `VERIFIED_LIVE`
- Eligible publishing shortlist = currently verified LIVE, ≤30-minute TTL, max two jobs per tenant
- Exact explicit closed state requires repeated observations at least 15 minutes apart
- Shadow artifacts: source audits, lifecycle counts, verification evidence and shortlist
- Regression tests for expired false positives, missing jobs, transient source failures, and duplicates

## Not implemented / known limitations

- Only three inventory sources are supported; Workday, SAP SuccessFactors, Oracle HCM,
  Phenom and custom portals remain coverage gaps.
- Source freshness is the **scan timestamp**, not the employer's original posting date.
- A record absent on multiple complete scans remains `CLOSURE_SUSPECTED` until strong
  exact-requisition closure evidence is established.
- One successful scan is not proof that a source returned every job; this version flags
  major count drops, but more provider-specific paging/completeness checks are needed.
- Published jobs with old LIVE checks must be reverified again before any future release.
- This branch has no job page generation, actual publishing, Telegram sending, secrets,
  production updates, or scheduler with side effects.
- Shadow history is cached by GitHub Actions and uploaded as a downloadable artifact.
  On an empty/missing cache, V3 rebuilds history rather than fabricating continuity.
- The small source sample does not establish real-world precision or discovery recall.

## Test

```bash
python3 -m unittest tests/test_job_radar_v3.py -v
python3 scripts/job_radar_v3.py --max-sources 3 --max-verify 6
```

**Production promotion is not authorized** and requires new evidence, statistical
calibration, safety review and separate user approval.
