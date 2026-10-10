# HD Careers Admin — Premium Native Android

Private Android Admin application for a Google Pixel 10a. Kotlin + Jetpack Compose, Material 3. **No Play Store account is required for direct personal installation.**

## Implemented in the development branch

- Secure login against existing HD Careers Admin APIs
- 4 native bottom tabs: Home, Review, Jobs, More
- Top 10 + Backup 10 review of actual server-side jobs: Live / Expired / Unsure, category-matched swaps, guarded publish
- Live job search, existing jobs, manual VIP job URL extraction and publish confirmation
- GA4 overview, 24H/7D/30D analytics, top countries/pages/devices, expiration checker
- Android Keystore credential encryption (only after a biometric/device credential challenge)
- FCM notification client and server-side authenticated token-registration APIs
- Daily unreviewed-batch reminder (WorkManager, approximate 9:30 AM IST; Android can delay it)
- GitHub Actions debug APK build and separate privately release-signed workflow

## Build locally

Install Android Studio, SDK Platform 35, JDK 17 and Gradle 8.9. Open the `android-admin` folder as a Gradle project, sync, then run on your Pixel 10a. For command-line use, `gradle :app:assembleDebug` produces a developer-signed APK at `android-admin/app/build/outputs/apk/debug/app-debug.apk`.

A debug APK is **temporary for testing**: GitHub Actions uses a generated debug signing key that could be different each time, so one debug artifact may not update another. For a stable long-term installation, use the **same private release keystore** on every build.

## Private signed APK

Create an Android release signing key once, on your Mac, with Java's `keytool`. **Do not store the keystore or passwords in GitHub code, chat messages, or the APK.** Make an encrypted backup.

Add these GitHub Actions repository secrets:

- `HD_ANDROID_KEYSTORE_BASE64` — base64 encoding of the keystore file, as a secret
- `HD_ANDROID_KEYSTORE_PASSWORD` — private keystore password
- `HD_ANDROID_KEY_ALIAS` — signing alias
- `HD_ANDROID_KEY_PASSWORD` — private key password

Trigger **Android Admin Private Signed APK** manually. The workflow refuses to build if the keystore secret is absent, verifies the signing certificate, and uploads the release APK as a short-lived private Actions artifact. Download it, install on Pixel, and keep the signing key for future upgrades. Turn on the Android "Install unknown apps" permission only for the trusted installer and turn it off afterward. Do not distribute the APK publicly.

## Firebase Cloud Messaging configuration

Create a Firebase project (Spark tier works for FCM), register the Android application id `in.hdcareers.admin`, and enable the Firebase Cloud Messaging API. No paid Play Store membership required.

In GitHub Repository → Settings → Secrets and variables → Actions → **Variables**, configure:

- `HD_FIREBASE_APP_ID`
- `HD_FIREBASE_API_KEY`
- `HD_FIREBASE_PROJECT_ID`
- `HD_FIREBASE_SENDER_ID`

These are Firebase Android app identifiers, **not** Firebase service-account secrets. For local Android Studio builds, provide `FIREBASE_APP_ID`, `FIREBASE_API_KEY`, `FIREBASE_PROJECT_ID`, and `FIREBASE_SENDER_ID` as Gradle properties or environment variables.

In Vercel → Project → Environment Variables (Production), configure **private server-only** secrets:

- `FCM_PROJECT_ID`
- `FCM_SERVICE_ACCOUNT_CLIENT_EMAIL`
- `FCM_SERVICE_ACCOUNT_PRIVATE_KEY` (actual PEM with escaped newlines supported)
- `UPSTASH_REDIS_REST_URL`
- `UPSTASH_REDIS_REST_TOKEN`
- `ANDROID_PUSH_DISPATCH_SECRET` — random secret of at least 32 characters

Configure `ANDROID_PUSH_DISPATCH_SECRET` with the **same exact value** as a GitHub Actions secret. The private Redis stores device registration and per-batch deduplication. No FCM service-account private key is embedded in the APK or committed in GitHub.

The `.github/workflows/android-review-notify.yml` job calls the authenticated Vercel dispatch endpoint when `data/daily-review-batch.json` changes. Delivery is attempted only for a recently generated **real** batch with 10 priority and 10 backup jobs. It is not a substitute for the discovery pipeline that populates the list. Firebase push delivery cannot be guaranteed to the exact second; Android permissions, internet and battery state affect timing.

## Current limitations

1. The existing batch data file is intentionally empty. The 9 AM discovery pipeline is **not yet wired** to populate its Priority 10 + Backup 10 automatically.
2. Real FCM pushes require your Firebase project configuration, securely configured server secrets, a signed installation, and a physical Pixel test.
3. Deploy and Telegram receipt status are not yet fully reconciled in-app; a successful Publish action only means GitHub accepted the request.
4. Biometric unlock is opt-in and available after an initial password login. The app will request a biometric/device-credential challenge before saving encrypted login credentials.

**Keep this work on a feature branch until the CI build passes, APK is installed on a real Pixel, and notifications are tested.**

## Premium Android interface (v1.1)

The Android app now uses the same HD Careers palette as the iOS Admin:
deep navy (#071A33), blue (#0969DA), cyan, violet, green, and translucent gradient heroes. The UI uses original Compose screens and retains server-side authenticated controls.

- **Official app branding:** The native launcher icon, login logo and header logo reuse the exact bytes from `assets/hd-careers-logo.png` in the repository.
- **Four premium tabs:** rich Overview with traffic trend, daily Review with replacement controls, Jobs with VIP draft tools, and More with full GA4 Analytics, notifications, expiry checker and security.
- **Analytics:** live stats, 24H/7D/30D filters, traffic sparkline, conversion cards, country and acquisition bars, top page ranking, device donut chart. Values come from the existing authenticated GA4 API, not sample data.
- **Pixel layout:** two-column metrics, full-width reports, readable labels and text wrapping. No cramped three-column reports.
- **No production changes:** install APKs from GitHub development CI only until real Pixel tests are successful.

The app's `versionCode` is 2 / version 1.1.0. GitHub debug APKs may use different signing certificates: uninstall the old debug APK if Android refuses the new installation. The private signed release will provide stable long-term updates.
