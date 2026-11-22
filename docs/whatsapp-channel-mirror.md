# HD Careers — WhatsApp Channel API bridge (Whapi.Cloud)

This is an optional integration with a **third-party, unofficial** WhatsApp web-session gateway. Meta's official WhatsApp Cloud API does not offer normal Channel post creation. Connecting a separate number as ADMIN reduces exposure of the original owner number but **cannot eliminate the risk of account restrictions or Channel issues**.

**Default state: DISABLED. No automatic sends until setup and owner opt-in.**

## Setup for existing 7K WhatsApp Channel
1. Activate a separate number with WhatsApp. On the existing 7K-member Channel, invite the new number as an **ADMIN** and accept the invitation on the new WhatsApp account. Keep the existing owner number as OWNER.
2. Create a Whapi.Cloud account (https://whapi.cloud) and pair **only the new number** via QR. Do not share QR codes, session data or API keys through chat.
3. In the Whapi dashboard, use GET /newsletters to identify the **existing Channel's internal ID**, ending in @newsletter. It is not the public whatsapp.com/channel invite URL.
4. Set GitHub Actions secrets **WHAPI_TOKEN** and **WHATSAPP_CHANNEL_ID** in Chethan-Mns/Hdcareers. Run Actions → HD Careers WhatsApp Channel Mirror → Run workflow → verify_only=true. This should confirm the connected account's ADMIN rights without posting.
5. Set GitHub Actions variable **WHATSAPP_CHANNEL_ENABLED=true**. The first enabled run stamps activationAt and deliberately **does not backfill historical Telegram posts**.
6. Subsequent confirmed Telegram posts trigger a mirror request. The workflow verifies the job remains active, checks exact employer source and the live HD Careers job page, confirms the ADMIN role, posts once via Whapi.Cloud and records its provider message ID.
7. To stop: change WHATSAPP_CHANNEL_ENABLED=false. If a send outcome is uncertain or the WhatsApp number is disconnected, review the Channel manually before attempting a resend; do not clear ledger records indiscriminately.

## Limitations
- Five-minute GitHub polling is a fallback; actual post timing may be delayed.
- POST /messages/text acceptance is not proof all 7K followers received or saw the message.
- The bridge does not send DMs or advertisements to individual users; it posts only to the Channel that grants ADMIN authorization.
- Never share the API token or WhatsApp QR/session contents in the repository, in screenshots or in chat.
- Existing Telegram receipts remain unaffected by WhatsApp failures.

Files: scripts/whatsapp_channel_relay.py, data/whatsapp-channel-deliveries.json, .github/workflows/whatsapp-channel-mirror.yml.
