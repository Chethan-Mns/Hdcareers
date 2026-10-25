# HD Careers Android Admin v2 — exception-first operations

**Audit date:** 17 Oct 2026
**Audited source:** `android-admin/app/src/main/java/in/hdcareers/admin/` on `main`, Android `versionName=1.2.2`, `versionCode=5`. This describes repository source, not a verified installed APK.

## Product goal

Replace repeated job-by-job review with an owner command center: discover up to 20 **new** jobs from distinct employers (10 priority + 10 backup), verify exact public application routes, publish up to ten eligible roles with one confirmation, deliver Telegram hourly without duplicate sends, and review expiry exceptions only. Deloitte-first and the approved 87 employer watchlist remain server-side discovery priorities. Never pretend unconfirmed availability is Live.

## Findings from current app

- `PremiumScreens.kt:273-412` displays Priority/Backup/Publish Ready and forces Live/Expired/Unsure review per candidate followed by Add to Publish Ready. `AdminViewModel.kt:134-175` triggers source enrichment only **after** selection and presents API acceptance separately from actual delivery. Extra steps obscure one-go publishing.
- `PremiumScreens.kt:484-583` displays VIP drafts and a read-only existing-jobs list; no native per-job expire/restore control or deployment receipt view.
- `PremiumMore.kt:271-331` hides expiry management under More and only shows generic Keep live / Expire job buttons; no official URL, last-check timestamp, evidence layer, multi-select, or resolution history.
- `api/admin/review.js:172-215` overloads Keep live on a pending new job to approve adding it to website data, while `api/admin/review.js:251-270` records `browserVerifiedAt` on an existing job without checking that the reviewer opened a matching exact application. Avoid using a button click as false source verification.
- `api/admin/publish.js:183-234` reports progress only for jobs selected in a saved daily-review publication, not all published routes or independently initiated VIP requests; it admits GitHub workflow matching is approximate. Current hourly queue `data/telegram-hourly-queue.json` is absent from the Android client.
- `AdminViewModel.kt:92-116` refreshes batch, jobs, logos, traffic, checker and automation sequentially, holds one global busy state and shows generic dialogs on errors. `PremiumScreens.kt:64-65` shows review notifications based on `reviewed<20` rather than actual exceptional blockers.
- `data/availability-status.json` had 120 checked, 113 active and 7 review in the 17 October snapshot. A review action should not conflate browser blocked/unconfirmed with expired.

## Proposed information architecture — 4 focused tabs

1. **Today (operations):** show 9 AM discovery status, 20 discovered / 10 priority / 10 backup, number of employer-watchlist jobs, ready-to-publish count, 8/1/1 actual category mix, exceptions, and next hourly Telegram item. No GA4 chart above daily actions; traffic behind a compact analytics action.
2. **Publish (two sections):** Source-verified Ready and Held / Backups. Job card shows official company logo, company, role, city, experience, source evidence and why held. Live/Expired/Unsure should be **verification evidence** rather than forced owner tasks. Publish All Eligible (<=10; distinct employers; no website duplicates) in a confirmation sheet. Explicit count of held and reasons. Keep additional jobs as backups, never relabel off-quota roles.
3. **Expiry Exceptions:** only unknown, conflicting, reopened or truly closed jobs needing owner intervention. Cards include exact official Apply link, requisition ID, check time, ATS/search/application-route evidence, and reason. Actions are Keep published (only after explicit source check), Confirm expired (with evidence & reversible audit), Retry check, or Hold. Bulk confirmation allowed only for explicitly marked items. No automatic expiry from HTTP 403/404/CAPTCHA/JS shell.
4. **Jobs & Delivery:** search active and expired website listings, job detail with Edit, Expire, Restore, Website, Official Apply and Telegram post. Separate delivery timeline with Source Checked → Accepted → GitHub committed → Vercel READY → Hourly queued → Telegram delivered (message ID). VIP URL extraction lives as a floating Add Job action with editable draft, duplicate preview and scheduled/immediate selector.

## Critical backend contract improvements

- New authenticated aggregate `GET /api/admin/operations` for authoritative counts and minimal jobs lists; avoid serial loading of analytics, logos, jobs and expiry status for the first paint. Return independent freshness timestamps.
- Server-provided `publishable` + `holdReasons` per job; client does not convert human `reviewedStatus` to ATS-source Live. A browser-verified event must include the exact verified URL, source evidence, reviewer identity and timestamp, never a fabricated `browserVerifiedAt`.
- Canonical jobs keyed by company normalized group + requisition ID + exact posting URL, including published/expired website history, archived job batches and pending Telegram deliveries. Show duplicate before selection; API blocks identical job and employer reuse.
- Stable publish request IDs and an atomic server-side publish/candidate approval operation. Avoid POST publish success followed by a separate status mutation that might fail; ambiguous outcome must never cause duplicate dispatch.
- Aggregate GitHub run/deployment/website proof plus `data/telegram-deliveries.json` and `data/telegram-hourly-queue.json` into real per-job stages. Distinguish queued, delivered, failed and uncertain.
- Split expiry actions: existing posted job `keep`, `expire`, `restore` and **new unpublished candidate** `reject`, `publish`. No overloaded “Keep live” for publishing new unpublished jobs.
- Respect owner vs job_editor authorization; never expose private GitHub tokens/Telegram tokens/FCM credentials on the device. All writes audited and idempotent.

## Delivery plan & acceptance tests

### Phase 0 — protect state (backend)
- Regression tests: generic redirect must be Review, manual “Keep live” requires matching source context and must not forge source verification; no extra Telegram post on retries.
- Maintain current records; migrate no existing job status on install.

### Phase 1 — make native app operational (new development branch only)
- Home first paint without sequential GA4 dependency; refresh in parallel with per-widget loading/error state; persistent notifications; preserve login.
- Publish board shows correct ready/held filters and exact source verification. One go confirmation of up to 10 with actual 8/1/1 eligibility and duplicate checks. Published receipts from both VIP and batch routes.
- Expiry Exceptions accessible in bottom navigation and links to exact career pages.
- Job Manager supports native expire/restore with confirmation and source evidence.

### Phase 2 — delivery ledger & hourly controls
- Show website page URL, Telegram message link/ID, queued position, last success, held reason, and current 60-minute cadence; override to VIP immediate only on explicit instruction.
- Local notifications for **actionable exceptions** and delivery errors, not repeated non-actionable '20 jobs awaiting review'.

### Phase 3 — device validation
- GitHub Android Debug build and unit tests, compare screenshots/flows on Pixel 10a including Android status bar and edge-to-edge.
- Update `versionCode` and `versionName`; private signed APK with same release key. Do not merge to production or ask owner to uninstall existing app until Android build, API tests, and owner UX review pass.

### Must-pass scenarios
1. 20 candidates discovered, only 6 fully verified: screen shows “6 ready, 14 held,” offers publishing only those 6, no forced quota padding.
2. 8 IT + 1 non-IT + 1 internship verified from 10 employers, none previously published: one owner confirm sends single idempotent request; site and Telegram stages independently reconcile.
3. Owner submits nine, one backup expires: no duplicate dispatch, 8 eligible publish, 1 holds with reason.
4. Already delivered nine posts + two newly approved jobs: show 9 delivered, 2 hourly queued, send only two new posts one per hour; no reposting messages #505–513.
5. Official job redirects to generic careers page, fails ATS check or is blocked: mark Review, do not mark Expired or publish as active.
6. Expiry API returns seven uncertain listings: show only seven as exceptions with official link, evidence & options; no requirement to mark 113 active listings.
7. A job editor’s ambiguous expired/active action cannot bypass owner approvals or alter published records without server audit.
8. Unverified manual candidate has missing eligibility / responsibilities: show missing fields; cannot fake source details or record Live proof.

This design spec is for owner review and implementation planning; no new Android build or production behavior is changed by this document.
