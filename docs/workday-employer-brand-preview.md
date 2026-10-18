# Preview: Workday job, real employer branding (development only)

## Concrete example from a public official job page
- Employer: **Deutsche Bank** (the hiring company, not Workday).
- Requisition: **R0357981** — Apprentice Hiring for 2026–2027.
- [Exact Deutsche Bank Workday job](https://db.wd3.myworkdayjobs.com/en-US/DBWebsite/job/Mumbai-Nirlon-Know-Pk-B4-B5/Apprentice---Non-Technology_R0357981).
- [Independent Deutsche Bank careers portal](https://careers.db.com/professionals/).
- [Company logo standards](https://uat.brandportal.db.com/our-visual-identity/Logo/index?language_id=1).

## Expected icon selection
1. The verified job says company: Deutsche Bank.
2. The curated company-logo-domains configuration maps Deutsche Bank to db.com, not db.wd3.myworkdayjobs.com.
3. Use an approved local image first. If absent, read icon tags from the independently verified careers.db.com website.
4. If there is no suitable careers logo, try the company's official corporate favicon at db.com.
5. Normalize/cache a high-quality accepted asset under assets/company-icons when the resolver runs.
6. If no trustworthy employer image exists, use neutral initials. Never display generic Workday, Greenhouse or Oracle Cloud branding.

## New check for exact Workday jobs
Only consider Workday strong Live when its public native exact-posting endpoint returns:
- A matching requisition ID
- A meaningful title
- Explicit positive application status (canApply true, isActive true, or an official apply URL)
- No explicit closed/inactive marker

A missing API, blank JavaScript shell, generic Apply label or isolated HTTP 404 produces Needs Review, not assumed Live/Expired.

## Manual acceptance check
- Confirm the job title, employer name and exact requisition
- Confirm actual application availability independently
- Review the site card: blue Deutsche Bank identity, not orange Workday
- Test a no-image/blocked-employer-icon fallback
- Inspect verified morning shortlist and two independent expiry fixtures

**Development only:** this example does not post, renew, or automatically mark R0357981 as currently open.
