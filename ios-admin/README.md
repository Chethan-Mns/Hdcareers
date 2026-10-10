# HD Careers Admin for iPhone

Private SwiftUI admin application for **Chethan** to manage HD Careers from an iPhone.

## Included in v1

- Secure HD Careers Admin sign-in
- Optional Face ID re-login backed by the iPhone Keychain
- Dashboard with job counts, GA4 traffic and automation health
- Active / expired job browser and search
- Paste and preview multiple official job links
- Generate job drafts through the existing HD Careers extraction API
- Edit generated job details before publishing
- Publish through the existing GitHub → generator → Vercel → Telegram workflow
- Run the Expired Job Checker
- Review uncertain jobs with Official / HD Careers / Remove / No Change actions
- 24H / 7D / 30D traffic analytics
- Daily Publishing Batch details for the consolidated 9:00 AM IST run

## Security

The app contains **no GitHub token, GA4 private key, Telegram token, or admin password**.

All privileged work remains server-side at `https://hdcareers.in/api/admin/`.
The native app uses the same secure admin session cookie as the web Admin.

If Face ID is enabled after sign-in, the admin username/password is stored only in the local iOS Keychain with `kSecAttrAccessibleWhenUnlockedThisDeviceOnly`. It is never committed to GitHub.

## Open in Xcode

Requirements:

- macOS
- Xcode 17+
- XcodeGen

Install XcodeGen:

```bash
brew install xcodegen
```

Generate and open the project:

```bash
cd ios-admin
xcodegen generate
open HDCareersAdmin.xcodeproj
```

Then select the **HDCareersAdmin** target → **Signing & Capabilities** → choose your Apple Development Team.

Bundle ID: `in.hdcareers.admin`

## Install privately on Chethan's iPhone

For a direct development install:

1. Connect the iPhone to the Mac.
2. Trust the Mac on the iPhone.
3. Choose the iPhone as the Xcode run destination.
4. Select your Apple Development Team.
5. Press Run.

For a long-term private install through TestFlight, an Apple Developer Program membership is required. The app can remain private and does not need to be publicly listed on the App Store.

## Branding

The app uses the existing HD Careers logo from:

`assets/hd-careers-logo.png`

The Xcode build prepares the App Icon from that same source image automatically.

## Version 1.1 — Priority/Backup Review Hub

- New **Review** tab with Priority 10 / Backup 10 and direct official application links.
- Save manual Live / Expired / Unsure decisions to the server via `/api/admin/daily-batch`.
- Replace a priority job with a *manually confirmed Live* backup from the same category.
- Require all ten priority jobs to be Live, with complete verified job content, before enabling Submit.
- Publishing uses the existing `/api/admin/publish` workflow. Submission is **not** proof that website deployment or Telegram delivery succeeded.
- Existing manual job entry and editing is in **More → Manual publishing**.
- Analytics cards adapt to narrow device widths and larger text without squeezing Countries/Devices together.
- An optional local notification reminds you daily at **9:15 AM IST** to check the review hub.
- A matching responsive web review page is at `/admin/review-batch.html` if the native iOS app cannot launch.

### Review batch data contract

The source of truth is `data/daily-review-batch.json`, served only through authenticated Admin API routes. A discovery workflow must populate the file with a unique `batchId`, `generatedAt`, `status: "draft"`, `priority` (10 items), and `backup` (10 items).

Each entry needs a stable string `id`, `company`, `role`, `loc`, `cat`, `apply`, and a complete canonical `job` object. Valid categories include `it`, `nonit`, `internship`, and `apprenticeship`. Optional `reviewedStatus` is `live`, `expired`, or `unsure`. An item is not publish-ready without an actual verified job description, eligibility, responsibilities, and official application link. Never synthesize facts just to reach a word-count target.

The file intentionally starts empty. It **does not** fabricate real discovered jobs. The 9:00 AM candidate discovery workflow still needs to be connected to this data contract.

### iOS notification limitations

**Free Personal Team:** Apple's development provisioning profiles expire after 7 days, even if the app is opened every day. Rebuild and reinstall it periodically. For a more durable installation, enroll in the paid Apple Developer Program and distribute with appropriate signing.

**Local reminder:** The Review screen offers an opt-in daily reminder at 9:15 AM India time. This is not a real-time server push. It does not claim the latest batch is ready.

**Native remote push:** To send a "20 jobs ready" alert when the app is closed, a paid developer membership, Push Notifications capability/APNs entitlement, APNs key, secure device-token storage, and server-triggered APNs delivery are required. Those are not configured by this branch; do not claim end-to-end push is operational.

### Install and review after merging

1. Pull the latest `main` branch on the Mac.
2. From `ios-admin`, run `xcodegen generate`, then open `HDCareersAdmin.xcodeproj`.
3. Set the Development Team, choose the connected real iPhone 15 Plus, and press Run.
4. Sign in; open **Review**, tap **Enable 9:15 AM reminder** and allow notifications.
5. Verify the Analytics page on the actual device with the preferred display and text-size settings.
6. Use `https://hdcareers.in/admin/review-batch.html` in Safari as a fallback while the native app needs re-signing.

CI builds an unsigned **iPhone Simulator** app. It cannot produce a signed device install or TestFlight release without Apple credentials and Xcode signing.
