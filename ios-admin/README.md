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
- Automation health details for 9AM / 12PM / 3PM / 6PM / 9PM

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
