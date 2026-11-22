# HD Careers Instagram Reels + SuperProfile Auto-DM readiness

Prepared on 22 November 2026. NOT CONNECTED OR LIVE.

## Existing repo workflows
- .github/workflows/daily-instagram-reel.yml: 7 PM IST daily, preview-first
- scripts/reel_factory.py: fresh verified job selection, caption, script, vertical video + optional ElevenLabs narration
- scripts/instagram_reel_publish.py: Meta Instagram Professional API publishing, when configured
- admin/reel-kit.html: manual Reel Kit
- data/reel-posts.json: publication/deduplication ledger
- scripts/reel_superprofile_handoff.py: prepares one job-specific SuperProfile Auto-DM DRAFT for each Reel manifest without sending

The previous inspected scheduled factory run returned no_eligible_verified_job because it did not find a recent confirmed-active job. This is a safe stop: never bypass verification merely to generate a Reel.

## Intended workflow
1. Owner approves a fresh live fresher job in HD Careers Admin.
2. Reel Factory prepares a 10–15 second script, caption, and a 9:16 Reel when approved footage and narration are present.
3. Owner reviews the output plus SuperProfile Auto-DM handoff draft, keyword APPLY, and exact HD Careers job link.
4. Instagram publishes only after authorization. SuperProfile Auto-DM is attached to the correct Reel and tested before activation.
5. Record Instagram media ID and per-post SuperProfile automation ID; never blindly repost on unknown results.

## Free-first route
Use GitHub Reel Factory and Meta publishing if authorized. SuperProfile free plan provides keyword comment-to-DM on posts and Reels (one keyword per automation, text and URL button), subject to Meta limits. Free does NOT include follow gating or scheduling. To send the exact job link for each Reel, attach an automation to that specific published Reel manually; a blanket APPLY automation cannot know which job the user meant. The new JSON draft artifact makes that attachment repeatable but does not activate it.

## Paid all-in-one route
SuperProfile Creator currently advertises $4.99 first month then $29 monthly and supports scheduling Instagram Reels with Auto-DM attached before posting. Schedule videos at least 15 minutes ahead and arm the Auto-DM at least 10 minutes ahead. Ask-to-follow before link is paid. Confirm pricing and plan rules at signup.

Its remote MCP endpoint is https://mcp.superprofile.bio/mcp using OAuth on plans supporting custom apps. It advertises Instagram schedule context, post draft/upload, attachment of Auto-DM and schedule/publish tools, but this SuperProfile connection is not yet installed and authorized in this ChatGPT session.

## Blockers and next steps
1. Connect an Instagram professional (Business/Creator) account with Meta API publishing permission.
2. Add reusable, owned/rights-cleared vertical footage to assets/reel-footage/ (no committed footage was found in the repo audit).
3. Configure optional ElevenLabs API key and voice ID as GitHub Actions Secrets, never source code.
4. Ensure a fresh official active-job verification scan before Reel Factory selection. Do not relax expiry rules.
5. Run the existing Daily Reel Factory manually with publish=false, review MP4/script/caption/Auto-DM draft artifact.
6. Choose free manual per-Reel DM binding vs paid SuperProfile scheduler + attached automation.
7. Test an exact link from a real Instagram comment keyword using a consenting test account.
8. Only then switch on public auto-publishing; keep the default preview mode for now.

## Safety
- No unsolicited Instagram DMs, credential scraping or unofficial browser automation.
- Ensure account consent for API scopes and keep posting secrets in GitHub Actions Secrets.
- Use five relevant hashtags; do not promise guaranteed reach or make up salary figures.
- Media and captions must match current active employer postings; do not edit a person's face/body without consent.
- Record provider receipts and do not blindly retry uncertain Instagram publishes.

References:
https://superprofile.bio/auto-dm/use-cases/comment-to-dm
https://superprofile.bio/guides/schedule-instagram-post-with-auto-dm
https://superprofile.bio/mcp/chatgpt
https://superprofile.bio/pricing
