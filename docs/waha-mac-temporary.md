# HD Careers — temporary WAHA on MacBook M4

This is free software with a free ngrok development tunnel. WAHA is unofficial WhatsApp Web automation and can trigger account/Channel restrictions. Use a separate WhatsApp number as ADMIN of the existing 7K Channel. Do not link the original owner account.

Status: repository deployment prepared only. Docker is NOT installed on your Mac by this commit. WhatsApp posting is disabled until credentials, verification, and your explicit opt-in variable are configured.

## 1. Install Docker Desktop
Get the Apple chip installer from https://docs.docker.com/desktop/setup/install/mac-install/ and open Docker Desktop. Use its qualifying free/personal license and wait for Engine Running.

## 2. Clone the HD Careers repo and start WAHA
Open Terminal. If you don't have the repo:

    cd ~
    git clone https://github.com/Chethan-Mns/Hdcareers.git
    cd ~/Hdcareers/deploy/waha-mac

If you already cloned it:

    cd ~/Hdcareers
    git pull --ff-only origin main
    cd deploy/waha-mac

Generate credentials and run:

    bash bootstrap.sh
    docker compose config --quiet
    docker compose up -d
    docker compose ps

Open http://localhost:3000/dashboard in Safari. Username: hd_admin. Password is stored in the local .env file, never in GitHub. Copy only to your own clipboard:

    grep '^WAHA_DASHBOARD_PASSWORD=' .env | cut -d= -f2- | pbcopy

Your WAHA API key (PLAIN text, not the sha512 hash in .env) is in .waha-api-key.secret. To copy it privately:

    pbcopy < .waha-api-key.secret

Never send the private key, WhatsApp QR or screenshot of .env to anyone. The local .gitignore protects these files from accidental commits.

## 3. Pair a dedicated WhatsApp number and existing Channel
On the localhost WAHA Dashboard start session "default" and scan QR using the dedicated WhatsApp account via Linked Devices. In your original 7K-follower WhatsApp Channel, invite this number as ADMIN and accept the admin role from the new account. Do not create another Channel.

Use the WAHA API explorer to GET /api/default/channels, which returns Channel ID and the current account role. Find the existing Channel with role OWNER or ADMIN. Save its exact Channel ID ending in @newsletter privately (the public Channel invite URL is not the API ID).

## 4. Secure free external access for GitHub Actions
Create a free account at https://dashboard.ngrok.com/signup . ngrok's free plan comes with a permanent assigned development hostname and monthly usage limits.

With Homebrew installed, run:

    brew install ngrok

Or use the official Mac download at https://ngrok.com/download/mac-os .
Copy the one-line "ngrok config add-authtoken" command from your own ngrok dashboard, and run it privately (never share its token).

In a SECOND Terminal window run:

    ngrok http 3000

ngrok forwards its assigned HTTPS dev domain to 127.0.0.1:3000. If necessary, use:

    ngrok http 3000 --url https://YOUR-ASSIGNED-DEV-DOMAIN

Do not use public router port forwarding or change hdcareers.in DNS. WAHA API auth and dashboard strong password stay enabled. Be aware that an HTTPS ngrok URL exposes an authenticated service on the public internet; follow all security precautions.

## 5. Connect HD Careers GitHub Actions
Repository Settings -> Secrets and variables -> Actions:
Add repository SECRETS (never paste in a public file or chat):
- WAHA_BASE_URL = the entire ngrok HTTPS dev URL, no trailing slash
- WAHA_API_KEY = plaintext secret from local .waha-api-key.secret (not the hash in .env)
- WAHA_CHANNEL_ID = exact Channel ID @newsletter

Do NOT set the WAHA_CHANNEL_ENABLED variable yet.

Open https://github.com/Chethan-Mns/Hdcareers/actions/workflows/whatsapp-channel-mirror.yml and run a manual workflow with verify_only = true. This checks remote WAHA HTTPS access and the ADMIN/OWNER role, without posting anything.

After successful verification, create the GitHub Actions VARIABLE WAHA_CHANNEL_ENABLED = true. First enabled run sets activationAt and deliberately skips historical Telegram posts. Only NEW Telegram deliveries after activation are eligible. The bridge preserves the original source live checks, website checks, durable claim ledger and no-blind-retry behavior.

## 6. Keep the Mac awake, stop safely
Docker Desktop must stay running, ngrok Terminal session must stay running, and your Mac must be plugged in, awake and online. A laptop that sleeps stops mirroring but Telegram keeps running. To temporarily prevent idle sleep while plugged in, open a THIRD Terminal and run:

    caffeinate -dimsu

Stop caffeinate with Ctrl+C. It may not prevent sleep when the lid closes, so use an external monitor/clamshell setup correctly if the lid will be closed.

Stop posting immediately by setting GitHub Actions variable WAHA_CHANNEL_ENABLED=false. Then stop ngrok (Ctrl+C), and in the waha-mac folder run:

    docker compose down

The local .sessions data remains and normally avoids QR re-pairing.

## 7. Move back to Oracle when A1 capacity returns
Use the existing OCI ARM setup at deploy/waha and update the same three GitHub secrets with its new URL/key. Verify the OCI server before re-enabling posting. Keep the shared delivery ledger to avoid duplicates.

Source documents:
https://waha.devlike.pro/docs/how-to/engines/
https://waha.devlike.pro/docs/how-to/channels/
https://ngrok.com/docs/gateway/domains
https://ngrok.com/docs/pricing-limits
