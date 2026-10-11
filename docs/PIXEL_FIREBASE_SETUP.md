# HD Careers Pixel Firebase + signed APK setup

The app is **in.hdcareers.admin**. Android initializes FCM programmatically from the four `BuildConfig.FIREBASE_*` fields; you do **not** need to commit `google-services.json`. Never commit Firebase service-account JSON or the Android signing key.

## 1. Firebase project

Register Android package `in.hdcareers.admin` in Firebase project `hd-careers-admin`. Firebase Android sender/project identifiers are client configuration, not the server credential.

## 2. GitHub Actions variables (client-side config)

Open [Repository Actions variables](https://github.com/Chethan-Mns/Hdcareers/settings/variables/actions). Create exactly these four **repository variables**:

| Name | Value |
| --- | --- |
| `HD_FIREBASE_PROJECT_ID` | `hd-careers-admin` |
| `HD_FIREBASE_SENDER_ID` | `222926415546` |
| `HD_FIREBASE_APP_ID` | `1:222926415546:android:3b6af71a3fcfe52be3c483` |
| `HD_FIREBASE_API_KEY` | Copy `client[0].api_key[0].current_key` from your downloaded Firebase Android configuration |

The repository does **not** contain the API key. Use the GitHub variables screen yourself. Restrict the API key in Google Cloud to appropriate Android usage where supported; Firebase API keys are not service-account credentials.

When the variables are set, manually run [Android Admin Build](https://github.com/Chethan-Mns/Hdcareers/actions/workflows/android-admin-build.yml) to produce a Firebase-enabled **debug** APK. Older builds made before the variables were added will not support Firebase pushes.

## 3. Vercel production server credentials

In [Vercel project settings](https://vercel.com/hd-careers/hdcareers/settings/environment-variables), set:

- `FCM_PROJECT_ID` = `hd-careers-admin`
- `FCM_SERVICE_ACCOUNT_CLIENT_EMAIL` = the `client_email` property of your *private* Firebase/Google service-account JSON
- `FCM_SERVICE_ACCOUNT_PRIVATE_KEY` = its `private_key` property (keep literal `\n` sequences or multiline PEM)
- `ANDROID_PUSH_DISPATCH_SECRET` = a freshly generated, random 32+ character secret

Do not upload the private service-account JSON into chat, GitHub code, or Android app. Generate the service-account key in Firebase **Project settings → Service accounts**, and ensure the service account is authorized for Firebase Cloud Messaging API. Enable Firebase Cloud Messaging API (HTTP v1) in Google Cloud if needed.

Enter `ANDROID_PUSH_DISPATCH_SECRET` with **identical value** as a GitHub Actions repository **secret**. The workflow `.github/workflows/android-review-notify.yml` sends only for fresh, complete, 20-employer review batches. New/changed review statuses alone do not trigger another push.

Your HD Careers Vercel free project already uses `KV_REST_API_URL` and `KV_REST_API_TOKEN`, which the push registration endpoint reuses through `lib/admin-store.js`. Production Vercel environment updates only reach deployments **after redeploying**.

## 4. Permanent signed APK (one-time Mac setup)

Generate a key once using Java 17+:

```bash
keytool -genkeypair -v -keystore "$HOME/hdcareers-release.jks" -alias hdcareers -keyalg RSA -keysize 4096 -validity 10000
```

Choose a strong keystore/key password locally. Back up the `.jks` securely (encrypted). In [GitHub Actions secrets](https://github.com/Chethan-Mns/Hdcareers/settings/secrets/actions), configure:

- `HD_ANDROID_KEYSTORE_BASE64` — Mac: `base64 -i "$HOME/hdcareers-release.jks" | pbcopy` then paste into GitHub secret
- `HD_ANDROID_KEYSTORE_PASSWORD`
- `HD_ANDROID_KEY_ALIAS` = `hdcareers`
- `HD_ANDROID_KEY_PASSWORD` (the password for the key, which can match the store password)

Run [HD Careers Admin Private Signed APK](https://github.com/Chethan-Mns/Hdcareers/actions/workflows/android-admin-private-release.yml) with **Run workflow**. The build refuses missing Firebase variables or signing credentials, verifies its own APK signature, and uploads a private artifact. Never lose the signing key: future updates require the same certificate.

If your Pixel already has a debug APK signed with a different key, you may need to uninstall the debug app to install the release APK (this clears local data; account stays on the server).

## 5. Live-device test

1. Sign into the app with your existing Owner or a Job Editor login.
2. In **More → Live push alerts**, tap **Enable Firebase notifications** and allow Android notification permission.
3. Verify the status reads **Registered for live job alerts**.
4. Tap **Send test notification**. The server must respond that FCM accepted it and the Pixel must actually receive it. Delivery is not guaranteed at an exact second.
5. Check notification tap opens the Review tab. Repeat on Wi-Fi and mobile data, and with app in background.

Do not claim success before this physical device test passes.
