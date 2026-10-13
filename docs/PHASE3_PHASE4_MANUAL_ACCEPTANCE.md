# HD Careers — Phases 2–4 acceptance handover

Status: **development preview only**. Do not merge before manual checks.
PR: https://github.com/Chethan-Mns/Hdcareers/pull/81
Phase 2 prerequisite: https://github.com/Chethan-Mns/Hdcareers/pull/80

## Phase 3 pilot
One employer: **AHEAD (official Lever API)**. Runs in read-only shadow mode with explicit `autoPublishEnabled: false`.
API inventory listing -> exact source identity -> independent per-posting positive check -> India-location check -> source-only content draft -> hold/review or draft-ready.
No job publishing, GitHub website writes, status updates, or Telegram activity.
Shadow report: GitHub Actions, `Phase 3 single-employer shadow publishing pilot` -> artifact `phase3-ahead-official-shadow-report`.
Latest read-only measured result as of 14 Oct 2026: 12 candidates checked, 5 draft-ready, 7 held, 0 publication-ready. These numbers change as real employer listings change.
Mocked tests also cover invalid UUID, source URL mismatch, wrong role, wrong company path, duplicate source, missing employer content, unconfirmed country, timeout, 403/404, duplicate published role and no publication side effects.

## Phase 4 site improvements
- All 130 generated job pages get Twitter and OG share metadata and existing canonical/robots semantics.
- PDF.js and Mammoth reader scripts download **only after** selecting a PDF or DOCX; TXT requires no reader dependency.
- Site analytics suppresses search query parameter forwarding in GA4 page URL and adds aggregate LCP/CLS telemetry, honoring the existing opt-out setting.
- Google JobPosting datePosted appears **only with source-confirmed employerPostedAt**; without it, the listing remains available but no rich schema is invented.
- Static growth audit counts live/expired records, validates canonical and robots, job pages, share metadata, sitemap, local SEO/trust pages, opt-out, dependency loading and historical date provenance.
- Preview audit: 130 job pages, 109 active database records, 21 expired database records, 0 SEO blockers, 51 historical jobs requiring verified employer posting dates for Google Jobs schema. These are NOT AdSense-approval guarantees.

## Manual browser test matrix
| ID | Page/action | Expected |
|---|---|---|
| M1 | Open Vercel Preview via PR #81 checks | Updated site with unchanged public design |
| M2 | Open `jobs/ahead-ms-noc-apprentice-intern-6-months.html` | Real job text and working official apply URL, social metadata in view-source |
| M3 | Open `jobs/rubrik-software-engineer-cloud-azure.html` | Unconfirmed source shows 'Verification pending'; not an invented verified-active claim |
| M4 | Open `jobs/eaton-apprentice-it-pune-687237633525.html` | Expired/closed state, no enabled Apply CTA, no JobPosting JSON-LD |
| M5 | On active job page, network tab, before resume upload | Neither pdf.min.js nor mammoth.browser.min.js downloaded |
| M6 | Upload a TXT resume | No PDF or DOCX library downloaded; resume matcher still runs |
| M7 | Upload a text PDF resume | PDF library downloaded only on selection; matching resumes succeeds |
| M8 | Upload a DOCX resume | Mammoth library downloaded only on selection; matching resumes succeeds |
| M9 | On mobile, test loading/navigation, logo, job cards and share preview | No header overlaps, old design preserved |
| M10 | Check GitHub Phase 3 run artifact and data/jobs.json | Pilot output is shadow-only; production statuses, deploy and Telegram count unchanged |
| M11 | Inspect `sitemap.xml` and JobPosting JSON-LD | Expired job omitted; unproven date does not create fake markup |
| M12 | Verify browser analytics opt-out before loading page | No GA4/Clarity initialization when opted out; note real network requests require browser inspection |

## Conditions to enable unattended publishing
- Preserve owner-confirmed ServiceNow closure in a separate verified production change, never infer expiry from a single 404.
- Add tested Rubrik and Visa ATS adapters so availability coverage improves; current pilot only covers AHEAD.
- Establish source-complete publishing content and website deployment/Telegram receipt end-to-end tests before treating draft-ready as publish-ready.
- Owner signs off on the latest manual browser matrix; shadow-mode report alone is insufficient to prove real Telegram delivery or AdSense approval.

## Release safeguards
- No live production jobs mutated.
- No real Telegram messages sent.
- Never mark closed solely due to 403, 404, timeout, CAPTCHA, or missing inventory entry.
- PR #81 is a stacked preview based on the unmerged Phase 2 changes.
