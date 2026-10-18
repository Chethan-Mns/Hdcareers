# Seven ATS source accuracy pilot — DEV ONLY

Date: 18 October 2026, latest external-readonly scan: 14:24 UTC.

**Status: QA complete, awaiting owner's seventh-source verdict. Not approved for production.**

## Why this is a safe pilot

- All exact official URLs are in `data/testing/ats-platform-seven-20261018.json`.
- Existing HD Careers Admin signed pilot **v1.3.4-test**, versionCode **10**, uses the same package ID; the QA review opens separately from normal Publish and **cannot send a real publish request**.
- The Android app retains the first six job IDs and locally saved Live/Expired/Unsure decisions.
- GitHub's read-only tester never writes `data/jobs.json`, expiry records, daily batch, or Telegram queue and receipts.
- Changes remain on draft PR #112, not production `main`.

## Evidence table

| ATS | Official employer/job | Previous owner | Exact-source checker |
| --- | --- | --- | --- |
| Greenhouse | SuperApp – Software Engineer, Backend | Live | Verified Live |
| Workday | Airbus – Internship Configuration & PLM | Expired | Unsure, safely withheld |
| Oracle Candidate Experience | JPMorganChase – Disclosure of Interest Analyst, requisition 210794554 | Live | Verified Live via rendered ID + title + enabled Apply |
| SmartRecruiters | HrRoll – Intern for Programming | Live | Verified Live |
| Lever | AHEAD – MS-EUS Apprentice/Intern | Live | Verified Live after typography-safe exact title comparison |
| Ashby | Almabase – Software Engineer | Expired | Unsure, safely withheld |
| SAP SuccessFactors career site | SIA Engineering Company – Aircraft Maintenance License Trainee (AMLT), requisition 767 | **Not yet reviewed** | Verified Live via exact requisition + matching title + active Apply link |

Read-only QA evidence: `.github/workflows/ats-seven-oracle-browser-qa.yml` artifacts. Snapshot for the old six owner decisions lives in `data/testing/ats-platform-six-owner-ground-truth-20261018.json`.

**Metric interpretation:** 4/4 previously owner-confirmed Live postings detected, 0/2 owner-confirmed Expired postings incorrectly marked Live. SuccessFactors is the seventh and needs owner confirmation; it is not part of the historical six-label accuracy denominator.

## Remaining non-availability eligibility issues

- JPMorganChase Disclosure of Interest Analyst **requires at least five years' relevant industry experience**. Being currently Live does **not** make it suitable for HD Careers' fresher feed.
- SIA Engineering is a **Singapore** training position with a lengthy service obligation. Treat this role as an ATS diagnostics fixture, **not as a recommended India fresher posting**.
- Both are hard-held from real publication regardless of QA simulation.

## Reviewer steps

1. Update HD Careers Admin to v1.3.4-test, then open **Publish → Seven-platform QA review**.
2. Your original six saved decisions should still appear; select the SIA Engineering row.
3. Follow its exact official SuccessFactors posting, check role, requisition **767** and actual job-bound Apply link.
4. Mark the seventh posting **Live / Expired / Unsure**; tap **Copy decisions** and paste the JSON into the conversation.
5. Test **Simulate Publish** to confirm no website or Telegram messages are sent.
6. Decide whether Oracle browser checks and official SuccessFactors probing should proceed to limited production shadow evaluation; do not merge PR #112 without owner approval.

## Safety requirements before a production merge

- Dev CI passing (precision, availability, daily review, generator, auth, Android).
- Trial run with employer portals that return access denied and login pages to ensure these remain Unsure.
- Confirm that the morning shortlist excludes positions outside fresher criteria, even if exact requisition is Live.
- Verify 8:15 AM / 8:15 PM expiry behavior and review handling for first and second closure scans.
- Bump future production Android versionCode to **at least 11** to upgrade over this signed test build.
