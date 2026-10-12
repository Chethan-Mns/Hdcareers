# HD Careers Discovery V3 — Phase 2 shadow validation

## Status

**Read-only discovery, not auto-publishing.** The working production GitHub → Vercel → Telegram pipeline remains unchanged. New candidate discovery has not been permitted to publish automatically yet.

## Official employer sources

- EY worldwide SuccessFactors listing: `careers.ey.com/ey/search/`. Country is accepted as India only when the employer's result row explicitly names `IN` or India. No guessing from URL alone.
- Deloitte South Asia India SuccessFactors listing: `southasiacareers.deloitte.com/go/Deloitte-India/718244/`. Results use offset URL segments `/25/`, `/50/`, etc., not EY's `startrow` query parameter. Promotional links outside actual result rows are ignored.
- HCLTech India jobs: `careers.hcltech.com/go/India/9553955/`. Page contains a dynamic openings widget. Until an authorized structured feed and full pagination can be identified, the scanner reports `partial` rather than claiming jobs have closed.

## Collection contract

Every candidate includes employer, title, original official job URL, stable hashed identity, URL listing ID, location/country evidence and explicit review status. Links found in a list are **listed_unverified**, not automatically Live. Exact role pages require canonical URL, matching visible title, and working application control to become **live**.

A snapshot is `complete` only if:

1. Robots permits access and all requests use the exact allowlisted employer hostname.
2. The official page provides result count, page number and pagination bounds.
3. Every page is retrieved; its unique job links match the advertised range.
4. Total number of results and page count do not change during the scan.
5. No overlapping job IDs/links occur between pages; final unique count matches reported total.

If any condition fails the snapshot is **partial**. It can supply candidate leads, but it is never evidence that absent previously published jobs have expired. If a job disappears from two fully complete sequential snapshots, it is only flagged for an independent closure check.

## Shadow operations

`python3 scripts/discovery_v3_full_list.py --max-pages 2 --verify-new 3`

The GitHub Action `discovery-v3-full-list-shadow.yml` runs tests and a shallow live sample on pull requests; after merge it runs a read-only daily shadow sample near **08:30 IST**, with six pages per employer and up to four exact job verifications. Workflow dispatch optionally supports up to 400 pages for a manually initiated full traversal. Completed reports are uploaded as temporary GitHub artifacts, never written to `data/jobs.json`.

Running more pages is not a guarantee of a full snapshot: changing totals, blocked HTTP requests, or HCLTech dynamic content still make results partial. The next rollout gate is to confirm full-list coverage and repeated accuracy before enabling V3 publication or expiry mutations.

## Production cutover gates

- Successful, complete official-scope source scans with reproducible evidence.
- Independent positive Live verification of every proposed posting; no invented details.
- Deduplication against published apply URLs and known employer requisition IDs.
- Freshers/experienced classification from actual vacancy details, not title guesses.
- Multiple shadow runs show no false-expiry decisions.
- Transactional publication only through the existing idempotent website/Telegram receipts flow.
