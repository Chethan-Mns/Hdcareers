# HD Careers — Free WAHA WhatsApp Channel relay (Oracle Always Free)

State: REPOSITORY CONFIGURED, NOT CONNECTED TO CLOUD HOST OR WHATSAPP. No messages are sent until the owner provisions WAHA, pairs a dedicated admin number, verifies it and enables the repo Actions variable WAHA_CHANNEL_ENABLED=true.

## Provider and risk
WAHA Core is free, open-source and documents posting to WhatsApp Channels using POST /api/sendText with session, chatId and text. It is NOT Meta's official WhatsApp Cloud API. Meta may restrict the WhatsApp Web session/number. Use a separate WhatsApp number with ADMIN rights on the existing Channel, retaining the original OWNER account. Neither free software nor using a separate number eliminates all restrictions or outage risk.

## Free hosting recommendation
Oracle Cloud Infrastructure (OCI) Always Free with an Ampere A1 ARM64 VM: 1 OCPU, 6 GB RAM, Ubuntu 24.04 ARM64, approximately 50 GB boot volume. OCI currently documents up to 2 OCPUs and 12 GB RAM in its Always Free Ampere A1 allowance, subject to tenancy eligibility, capacity, account limits and idle-instance reclamation. Avoid selecting paid instance shapes, block storage or bandwidth add-ons. Set spending alerts. If OCI displays OUT OF CAPACITY, a free always-on VM is not immediately available in that region; try a different available eligible region if your tenancy permits, or use a qualified Google e2-micro Free Tier VM only after testing its 1 GB memory limit. WAHA itself is free, hosting is not guaranteed free with all providers. Vercel Functions cannot host a persistent WhatsApp Web session.

Oracle official Always Free details:
https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm

## Provision server and secure DNS
1. Sign in to https://cloud.oracle.com/ in YOUR OWN account. In OCI Compute create Always Free VM.Standard.A1.Flex (Ampere A1), 1 OCPU / 6 GB RAM, an eligible Ubuntu ARM64 image and a public IPv4 address. Add an SSH key.
2. In OCI Virtual Cloud Network security rules, allow inbound TCP 80 and 443 for Caddy HTTPS certificates and WAHA access. Restrict SSH TCP 22 to the owner's IP. Do NOT expose port 3000. Retain the root hdcareers.in and www Vercel DNS entries as-is.
3. Add a DNS A record for a separate host such as waha.hdcareers.in pointing to the OCI VM public IPv4. HTTPS via Caddy requires the hostname to resolve to the VM and TCP 80/443 to be reachable.
4. SSH into the Ubuntu VM and install Docker Engine and the Docker Compose plugin using the official Ubuntu installation guide: https://docs.docker.com/engine/install/ubuntu/.
5. Clone the HD Careers repo onto the VM and generate PRIVATE local secrets:

       git clone https://github.com/Chethan-Mns/Hdcareers.git
       cd Hdcareers/deploy/waha
       bash bootstrap.sh waha.hdcareers.in
       sudo docker compose up -d

   Use YOUR chosen hostname in the bootstrap argument. bootstrap.sh refuses to overwrite old keys, creates a local .env, hashes the WAHA API credential as sha512, and keeps the plaintext API key in .waha-api-key.secret (not committed). Keep both files protected with chmod 600.
6. Check that sudo docker compose ps shows the free WAHA NOWEB ARM image running and that your HTTPS hostname loads the WAHA dashboard. Caddy automatically requests TLS certificates. On first boot it can require time for DNS/TLS.
7. In WAHA dashboard, sign in using username hd_admin and the private password from the local .env file. Connect the NEW separate WhatsApp number via dashboard QR. Do NOT share QR, dashboard password, SSH keys or session tokens in chat.
8. In the OWNER WhatsApp account of the existing 7K-member Channel, invite this separate WhatsApp number as ADMIN. Accept the invitation on the connected number. Do NOT create a new Channel.

## Connect WAHA to GitHub Actions
1. In the connected WAHA API/dashboard, GET /api/default/channels lists channels with ID, name and role. Find your EXISTING Channel where role is ADMIN or OWNER, and copy the exact ID ending in @newsletter. The public whatsapp.com/channel invite link is NOT the API ID.
2. In GitHub repository Settings -> Secrets and variables -> Actions, add three repository SECRETS:
   * WAHA_BASE_URL: your full HTTPS server address, for example https://waha.hdcareers.in
   * WAHA_API_KEY: the plaintext key from the VM's PRIVATE .waha-api-key.secret file, not the sha512: string from .env
   * WAHA_CHANNEL_ID: the exact @newsletter Channel ID from WAHA
   The previous WHAPI_TOKEN secret is no longer read. Once migration works, revoke the old Whapi session and token.
3. In GitHub Actions, open HD Careers WhatsApp Channel Mirror (WAHA). Use Run workflow with verify_only=true. This checks HTTPS, the API key and exact OWNER/ADMIN role. It does NOT publish anything. Leave WAHA_CHANNEL_ENABLED unset until this succeeds.
4. After successful verification, create GitHub Actions repository VARIABLE WAHA_CHANNEL_ENABLED=true. First enabled run writes activationAt to data/whatsapp-channel-deliveries.json and deliberately DOES NOT backfill historical Telegram posts. Only new Telegram receipts after activation are eligible.
5. Observe the next Telegram job delivery and the first WhatsApp Channel post manually. Successful WAHA API acceptance is saved to the ledger as provider_accepted, with the WAHA message ID. This does not prove every Channel follower saw the post.
6. To pause all WhatsApp posts, set WAHA_CHANNEL_ENABLED=false. If an attempt is uncertain, inspect the Channel and ledger before attempting a manual reconciliation. Never delete claims or automatically resend an ambiguous outcome.

## Publishing safety preserved
- Only a job with a confirmed message ID in Telegram @HD_Careers can enter the WhatsApp relay.
- The job must still be active in data/jobs.json.
- Immediately before sending, a fresh exact official-source check must return active. Errors, CAPTCHA, 404, unsure and expired are withheld.
- HD Careers public job page must be reachable and verified as active.
- WAHA must confirm the linked number is ADMIN/OWNER of exactly the configured Channel.
- Every WhatsApp post has its own durable pre-send claim, response receipt and no-auto-retry behavior; duplicate URLs are not blindly posted.
- Telegram initial sends and hourly sends both wake this mirror. A five-minute schedule is backup and may be delayed.
- Different WhatsApp account/session credentials never appear in public repo files.

## Cloud operations
The docker compose file and Caddy HTTPS config are in deploy/waha. Docker session storage is in deploy/waha/.sessions on the VM and must be backed up securely. Updating the VM/restarting Caddy does not wipe sessions while the volume is preserved. Keep the VM, Docker, Caddy and WAHA updated, and configure uptime monitoring. Oracle may reclaim unused Always Free instances as documented.

Official WAHA:
https://waha.devlike.pro/docs/how-to/channels/
https://waha.devlike.pro/docs/how-to/security/
https://waha.devlike.pro/docs/how-to/install/
