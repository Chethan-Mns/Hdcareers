# HD Careers Phases 3–4: production-reconciled acceptance guide

Status: **development only**, no production merge and no Telegram sends.

## Reconciliation
- Old PR #81 had 130 generated pages and predates 15 October owner verification.
- Current 131 production job records, all 39 owner decisions, Cognizant Service Desk #149, and the Telegram delivery ledger are authoritative. Regenerate HTML on the development branch from those records; do not restore stale generated pages.
- Phase 2 fixes in PR #82 are the prerequisite to merging Phases 3–4. No old test fixture may override newer owner evidence.
- The preview branch contains newer Phase 2 safety fixes; never merge it ahead of Phase 2 sign-off.

## Phase 3 discovery
- Read-only AHEAD Lever employer-feed pilot, with exact-posting ID/title, source page, India location, duplicate and description checks. Draft-ready does not mean publish-ready. No automatic deployment/Telegram messages.
- Timeouts, CAPTCHA and contradictory signals are REVIEW, not automatically expired.
- Before fully automatic publishing, validate source-specific adapters, a real website publication canary, durable Telegram receipt/idempotency, and two actual daily scheduled expiry runs.

## Phase 4 growth
- Social OG/Twitter meta and canonical/robots on regenerated pages.
- Lazy-load PDF.js/Mammoth only when the matching PDF/DOCX resume is uploaded; TXT needs neither library.
- JobPosting `datePosted` only when an employer-posted date is independently sourced. Historical editorial dates are not proof.
- GA4 page_location excludes query parameters; privacy-respecting LCP/CLS metrics follow analytics opt-out.
- SEO static audit verifies 131 pages, nine owner-expired job pages closed/noindex/absent from sitemap and all 30 owner-confirmed Active jobs preserved.
- Passing static audits does not establish AdSense approval or real-device performance.

## Manual acceptance before merging
1. Preview on desktop, iPhone and Android: logo, theme, header, job cards, filters and no overlaps.
2. Check all 9 owner-expired pages: no Apply CTA, no JobPosting and no sitemap URL.
3. Check all 30 owner-active pages still live on preview with exact employer links.
4. Check Cognizant Service Desk #149 has original Superset URL.
5. Inspect resume checker before upload: neither PDF.js nor Mammoth downloaded. Upload valid TXT, PDF and DOCX and check skills output.
6. Check real share previews and analytics opt-out.
7. Review Phase 4 audit warnings and performance: target LCP <=2.5s, CLS <=0.1.
8. Check official employer links and no failed or duplicate Telegram sending.
9. Owner review of NielsenIQ #82 and Deloitte USI #75 is still needed for ground truth; do not auto-reopen on HTTP-only evidence.
10. Regenerate site and compare against latest production owner review without any data/ledger mutations.

Production remains unchanged by these steps. PR #81 remains draft until the above tests pass.

## Automated reconciliation evidence — 15 October 2026
- Two-round actual employer source smoke test completed on draft PR #82, GitHub Actions run 38778826649. The rounds were separated by >=60s, not separate daily scans. No status edits.
- Draft PR #81 now has the latest production job data and Phase 2 safety code in its merge ancestry; old 130-job generated HTML was replaced by 131 regenerated pages on branch only, commit 5c8f510a56f7e14596a616083bcfb7acda47947a.
- Reconciliation generator workflow run 38779819079 passed, confirmed 131 records (100 active, 31 expired), preserved 39 manual decisions and Telegram receipt ledger, and reported 0 blocking growth-audit findings.
- This is development evidence only, not owner approval to merge into main.
