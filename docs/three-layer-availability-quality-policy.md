# HD Careers: Three-layer job availability verification

## Principle

A vacancy is **Verified Live** only if the exact public requisition is open for applications now. An HTML 200, a title in Google, an isolated search-result hit, or an unauthenticated login page is insufficient. 100% accuracy is not achievable from public-only signals: internal ATS state may require employer authorization, browser/region results may differ, and the employer may close a posting between checks.

Respect published API contracts, access permissions, robots constraints and limits. No CAPTCHA bypass, no use of private ATS credentials, no candidate applications submitted merely to test an endpoint.

## Three evidence layers (in order)

1. **Public job-posting API or employer XHR:** identify the exact public ATS tenant, posting ID and returned title; confirm the posting is published/available where the provider explicitly exposes that state. Only use verified vendor-specific field names, not made-up universal keys such as `jobRequisition.status` or `isPostingActive`. For Workday/SuccessFactors/Phenom/custom portals, inspect the actually used *public* request for the particular employer and version in a read-only browser and record what has been validated; do not assume it is stable.
2. **Active public search/listing:** retrieve a complete, relevant public listing for the same job ID, taking account of pagination, filters, geolocation, audience and locale. An exact hit supports Live; zero results alone is **Review**, not Expired. Absence in a partial list proves nothing. A closed/public-unpublished employer-authenticated field or authoritative deadline is stronger.
3. **Application route:** inspect the actual visible Apply control and follow its safe, public GET navigation to a job-specific application form. Require the original requisition to be retained in the form payload or unambiguously bound to its application form. A generic careers landing page or login page without persistent requisition context is **Review**. Never POST a test application or fill a candidate identity.

## Classification and release gates

| State | Evidence | Publishing action |
| --- | --- | --- |
| Verified Live | Exact post + current public published/open signal + matching public application route; or another documented set of independent employer signals | Publish after deduplication and eligibility check |
| Review | Bot block, generic redirect, SPA shell, HTTP 404 alone, search-index absence alone, conflicting signals, stale evidence, or missing job context in an Apply/login route | Do not publish; send to exceptions with URL and reason |
| Confirmed Expired | Explicit official exact-posting closed/unpublished state, expired authoritative deadline, or corroborated employer closure evidence | Skip publication; preserve source evidence and any prior owner decisions |

Check each job again immediately before deployment and Telegram delivery. Keep `review` distinct from `expired` so false closures are not accidentally applied to active jobs. Never treat an owner-confirmed Live job as freshly active indefinitely; compare current exact-ID evidence. Never close current jobs solely because a public portal is temporarily blocked.

## Cisco redirect regression

Cisco `projectId=1443859` was observed by the owner to redirect to the generic careers home page instead of its specific application. The historical indexed job detail is not proof of a functioning current application. Treat the exact URL as Review until a current, job-specific application route is demonstrated. Do not publish by replacing the job URL with a Cisco homepage.

## Evaluation plan

Save the October 17 owner-verdict benchmark as regression-only evidence. It has eight owner-confirmed Live, four owner-confirmed Expired, one Unsure. Previous checker output: eight Live, five Review; no false Live among those eight, but zero positively detected Expired in that small benchmark. Abstention is safer than an unjustified live claim, but discovery quality and confirmed-expiry recall need improvement.

Before enabling unattended API-based expiry changes, validate on at least **100-200 independent exact postings**, spread across ATS families and preferred employers, including known Live, known Expired, challenging generic redirects, unrenderable pages and conflicting source states. Report:
- Live precision, Live recall
- Expired recall and Expired precision
- Uncertain/Review rate (abstention coverage)
- Published jobs with post-delivery verification success
- Major-employer share, fresher eligibility fidelity and repeated-employer rate

Quality targets, not guarantees: >=98% verified-Live precision, >=95% expired recall on determinable cases, 0 known invalid generic apply links published. Protect correct existing Live postings against false automatic expiry.

## Audience/employer preference

Use the owner priority list in `lib/review-ranking.js` (Deloitte, EY, KPMG, PwC, Accenture, TCS, Infosys, Wipro, HCLTech, Cognizant, Capgemini, Tech Mahindra, Dell, HP/HPE, Landmark Group, CGI, Flipkart, Amazon, JPMorgan, Microsoft, Google, Cisco, etc.). Prefer one company per daily shortlist and reduce repeat employers based on Telegram delivery receipts. Rank major-brand job offers higher **only after** exact source and fresher eligibility are credible. A major-brand but closed or non-fresher position must never displace a verified qualified position.

These instructions do not activate a new public API adapter or bypass existing publication safeguards.
