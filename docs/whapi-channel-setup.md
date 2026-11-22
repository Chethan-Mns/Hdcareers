# HD Careers — Whapi.Cloud WhatsApp Channel relay

**Status:** Integration code prepared, but DISABLED. No messages are sent until the owner links their WhatsApp account, verifies the existing Channel and opts in using GitHub Actions.

This removes the requirement for Oracle hosting or a MacBook running WAHA. Whapi.Cloud uses an **unofficial linked-device WhatsApp session**, not Meta's official WhatsApp Business API. Prefer a dedicated HD Careers number with ADMIN rights on the existing Channel, retaining the original OWNER account.

## Publishing behavior

- Mirror only **confirmed Telegram @HD_Careers deliveries** after owner approval, never all jobs indiscriminately.
- Require the job to remain active, pass a fresh official-source check, and have a reachable HD Careers job page.
- Require OWNER or ADMIN role of the exact configured WhatsApp Channel, checked immediately before sending.
- Persist a pre-send claim to prevent duplicate posts; ambiguous results are held for manual reconciliation.
- Store Whapi acceptance and message ID, not an unverified claim of subscriber delivery.
- No historical Telegram deliveries are backfilled on first activation.
- GitHub Actions runs without keeping your MacBook online.

## Owner setup

1. Open https://panel.whapi.cloud/ and register for the **Developer Sandbox**. Whapi describes a no-expiry development-only Sandbox with limits: 5 conversations/month, 150 messages/day and 1,000 requests/month. Onboarding may begin with a 5-day trial: confirm your channel's mode is Sandbox afterward.
2. Scan the pairing QR from your phone: WhatsApp > Settings > Linked devices > Link a device. Prefer a dedicated number. If the existing HD Careers Channel belongs to another number, invite the connected account as Channel **ADMIN** and accept.
3. Use Whapi's GET /newsletters API to obtain the **exact Channel ID ending in @newsletter**. The public WhatsApp Channel invite URL is not the API ID.
4. Add GitHub repository Actions **secrets** at https://github.com/Chethan-Mns/Hdcareers/settings/secrets/actions :
   - WHAPI_TOKEN: Whapi dashboard API bearer token (keep private)
   - WHAPI_CHANNEL_ID: exact existing WhatsApp Channel ID ending in @newsletter
5. Leave GitHub Actions variable WHAPI_CHANNEL_ENABLED unset/false and set WAHA_CHANNEL_ENABLED=false. The two relays must not be enabled simultaneously.
6. Review and merge the Whapi integration PR. Under GitHub Actions choose **HD Careers WhatsApp Channel Mirror (Whapi.Cloud)**, select Run workflow with verify_only=true. It checks the Channel role without posting.
7. After successful verification set repository Actions variable WHAPI_CHANNEL_ENABLED=true. The first enabled run records the activation time and skips historical Telegram posts.
8. Observe the next newly approved job in Telegram and in the WhatsApp Channel. Confirm its delivery manually before relying on the setup.

## Safeguards and free-plan boundaries

- WHAPI_CHANNEL_ENABLED=false pauses future WhatsApp posts without changing HD Careers website or Telegram.
- Unknown API responses become uncertain; review the Channel and ledger before manual reconciliation. Never blindly retry.
- At 10 posts/day, one role-check and one post each is about 600 API calls/month, before any other API use. Stay below the 1,000-call cap.
- A free developer Sandbox may not be suitable for unattended production broadcasting. Published limits are not a production SLA.
- Both Whapi and WAHA rely on unofficial sessions and carry WhatsApp account-restriction and outage risk.
- GitHub Actions scheduled workflows may be delayed.
- The shared WhatsApp ledger is data/whatsapp-channel-deliveries.json; avoid enabling both providers together.
- Never share the token, pairing QR, passwords or session credentials in a public repo or chat.

## Provider references

https://support.whapi.cloud/help-desk/getting-started/pricing
https://support.whapi.cloud/help-desk/channels/send-post-to-whatsapp-channel-newsletter
https://whapi.readme.io/reference/getnewsletters
https://whapi.readme.io/reference/getnewsletter
https://whapi.readme.io/reference/sendmessagetext
