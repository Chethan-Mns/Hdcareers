# HD Careers — Whapi.Cloud daily WhatsApp Channel publishing

## Current integration

HD Careers approved jobs publish to the website first. Only confirmed Telegram @HD_Careers message receipts are eligible for the Whapi.Cloud relay. The destination is the existing **HD Career Updates** WhatsApp Channel, ID **120363419928883930@newsletter**. The original **HD Careers** Channel is deliberately excluded.

Whapi.Cloud is an unofficial WhatsApp linked-device provider, not Meta's official WhatsApp Cloud API. The account was manually switched by Whapi support to its free Sandbox on 22 November 2026. Free Sandbox messages are subject to provider fair use and restrictions; it is not a guaranteed production SLA. No MacBook, Oracle VM or Docker host is required.

## Exactly what gets posted

The message is formatted using `scripts/whatsapp_channel_relay.py:fmt`, shared by WAHA and Whapi, with a consistent Vercel preview from `api/whatsapp/latest.js`. Every message uses exactly these sections (only real job data is inserted):

```text
*Deloitte is Hiring ✅*

Role: Executive - Data Analysis (MS Excel)
Qualification: Graduate
Experience: Zero-experience eligible; no minimum experience stated
Location: Delhi/NCR, India

Apply Link: https://hdcareers.in/jobs/deloitte-executive-data-analysis-ms-excel.html

𝗝𝗼𝗶𝗻 𝗢𝘂𝗿 𝗪𝗵𝗮𝘁𝘀𝗔𝗽𝗽: https://whatsapp.com/channel/0029VbAxOna7NoZvhuKX362z
𝗝𝗼𝗶𝗻 𝗢𝘂𝗿 𝗧𝗲𝗹𝗲𝗴𝗿𝗮𝗺: https://t.me/HD_Careers
```

No invented salaries, package estimates, category, unnecessary emojis or extra promotions. Qualification and experience are taken from the job data when provided; otherwise the sender clearly labels eligibility or uses supported fresher classification.

## Automation path

1. Owner approves eligible fresher jobs in the admin review pipeline.
2. Website deploys approved jobs and records an active public job page.
3. Telegram sends the first job immediately and remaining jobs through the hourly queue; receipt + message ID are written to `data/telegram-deliveries.json`.
4. Both the initial admin publisher and hourly Telegram workflow dispatch `whapi-channel-mirror.yml` after confirmed Telegram receipts.
5. Whapi workflow checks owner opt-in at `data/whapi-channel-config.json`, exact Channel ID, and private GitHub Actions secrets.
6. The relay claims only unposted Telegram receipts AFTER `activationAt` in `data/whatsapp-channel-deliveries.json`, at most 10 per India-calendar day.
7. Before sending it verifies the job remains active, the exact official application source is live, the HD Careers public page is active, and the linked account remains Channel ADMIN/OWNER.
8. The Whapi API accepts the message, returns a message ID and the ledger persists provider acceptance; unknown outcomes are held for manual reconciliation.
9. A 15-minute backup schedule catches missed dispatches; GitHub scheduled workflows may be delayed.

## Configuration and operations

- `WHAPI_TOKEN` and `WHAPI_CHANNEL_ID` are GitHub Actions **secrets**, NOT checked into the repository.
- `data/whapi-channel-config.json` is the owner-controlled config. `enabled: false` pauses posting. `enabled: true` activates the verified Telegram receipt mirror.
- The actual approved Channel ID must equal `120363419928883930@newsletter`. A mismatch blocks sending.
- The legacy `WAHA_CHANNEL_ENABLED` GitHub Actions variable must be absent/false; the Whapi workflow refuses simultaneous operation.
- Initialize `data/whatsapp-channel-deliveries.json` `activationAt` immediately BEFORE enabling to avoid historical Telegram reposts. Preserve old test receipts.
- `MAX_DAILY_POSTS=10` limits API consumption and avoids exceeding free Sandbox quotas. A blocked or uncertain job is NEVER automatically re-sent.
- The free Sandbox has reported limits of 150 messages/day, 5 conversations/month, 30 WhatsApp checks/day and 1,000 API calls/month. Ten posts/day with one per-post admin check use roughly 600 API requests/month, excluding setup and other operations.
- The existing Channel is treated as one conversation, but Sandbox use for ongoing business production remains subject to Whapi's policies and availability.
- Inspect GitHub Actions workflow results and the `data/whatsapp-channel-deliveries.json` ledger for acceptance. A provider message ID is not guaranteed follower delivery.

## Disable or investigate

- To stop future posts: change `data/whapi-channel-config.json` to `enabled: false` on main.
- For uncertain results: inspect the Channel and GitHub ledger. Do not erase the claim and blindly retry.
- For lost Whapi connectivity: check paired account sessions and Channel Admin rights. Never publish a QR, token or linked-device credentials.
- When needed, use `workflow_dispatch` with `verify_only: true` to check Channel access without publishing.

## Official API references

https://support.whapi.cloud/help-desk/channels/send-post-to-whatsapp-channel-newsletter
https://whapi.readme.io/reference/getnewsletter
https://whapi.readme.io/reference/sendmessagetext
