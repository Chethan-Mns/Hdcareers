# HD Careers — fully automated Instagram Reel + SuperProfile design

Owner account: **@hd_careers** (active). NEVER use the inactive @hdcareers.

## Daily automated flow

1. GitHub Actions daily-instagram-reel.yml runs at 7:00 PM IST.
2. reel_factory.py selects only an active, freshly verified, eligible and nonduplicate fresher job. Unknown/expired listings are held.
3. reel_voice_elevenlabs.py generates Sarah narration (voice ID EXAVITQu4vr4xnSDxMaL) using the with-timestamps endpoint. It does not synthesize with a different voice silently.
4. reel_video.py shows the owner's approved 9:16 office footage full-screen. The correct company logo appears at the top, ABOVE the role; small word captions at the bottom highlight the word being spoken in magenta.
5. reel_preflight.py blocks incomplete renders, missing logos, misaligned captions, invalid job pages and promotional audio lacking confirmed commercial rights.
6. superprofile_oauth.py refreshes the GitHub runner's independent, rotating SuperProfile OAuth tokens with encrypted at-rest storage and commits the rotated ciphertext before scheduling.
7. superprofile_reel_bridge.py reuses the matching draft when present, uploads the finished MP4 from GitHub Actions via SuperProfile's one-time signed file URL, verifies the exact job-specific Auto-DM, and schedules publication at least 30 minutes ahead.
8. The attached DM uses ANY comment, a 30-second primary delay, an ask-to-follow gate, and the exact HD Careers job-link button. After a confirmed schedule, GitHub records the post ID, Auto-DM ID and job ID to prevent duplicates.

**No silent substitute voices, no unsolicited DMs, no wrong job links, no unconfirmed "published" claims.** 30 seconds is a configured delay, not a guaranteed delivery time. Scheduled status is not proof of successful Instagram publication.

## One-time setup requirements

### Rights-cleared reusable footage

ChatGPT conversation videos are not accessible from GitHub Actions. Upload one or more original or licensed MP4s once to the repo folder assets/reel-footage/. The pre-existing uploaded clips can be reused after this step. Avoid showing another employer's branding on a Brillio Reel.

### Separate SuperProfile GitHub worker OAuth

The SuperProfile login connected to ChatGPT is **not** transferable to GitHub Actions. On a trusted Mac with the HD Careers repo checked out:

    python3 -m pip install "cryptography>=44,<48"
    python3 scripts/superprofile_oauth.py connect

The script opens SuperProfile OAuth in a browser and asks for scheduling and Auto-DM permissions. It produces data/integrations/superprofile-oauth.enc.json containing encrypted refresh-token state. Commit ONLY this encrypted file. It prints SUPERPROFILE_FERNET_KEY only in the local terminal; add that value as an encrypted GitHub Actions repository secret. NEVER paste it into ChatGPT or commit it.

A short-lived SUPERPROFILE_MCP_ACCESS_TOKEN GitHub Actions secret also works for a one-off test but will expire and is not sufficient for daily unattended use.

### Rights to use Sarah's voice commercially

ElevenLabs free plans do not grant commercial-use rights for promotional Reels. Also, the old Sarah Default voice expires on December 31, 2026. The pipeline creates previews but blocks automatic promotional publishing until appropriate rights are legitimately obtained and GitHub variable HD_REEL_AUDIO_COMMERCIAL_LICENSE_CONFIRMED is explicitly set to true. Never turn this variable on without rights.

For a no-cost commercial voice, first select a provider with verified licensing and approve the new voice; the pipeline must preserve real word-aligned captions. An Instagram trending song cannot simply be licensed or attached by the Meta publishing API; use separately rights-cleared audio when authorized.

### Turn on unattended posting after prerequisites are verified

The ElevenLabs API key is already configured. Once the footage, SuperProfile worker OAuth, and commercial voice usage are in place, set GitHub Actions repository variable HD_REELS_AUTOPUBLISH to true. Start by triggering daily-instagram-reel.yml manually with publish=false to review output. Future daily jobs run without manual approval.

Pause immediately by setting HD_REELS_AUTOPUBLISH=false.

## What is implemented versus live

Implemented and tested: verified-job selection, Sarah word timing, small logo above role, 1080x1920 rendering, exact job-specific Auto-DM construction, 30-second timing, duplicate safeguards. Synthetic CI-only video render passed.

Code implemented but not production tested: independent OAuth + encrypted rotation and direct GitHub-to-SuperProfile upload/scheduling bridge.

Not yet provisioned: reusable original clips in the repo, separate GitHub runner OAuth consent, confirmed commercial voice rights. Therefore live fully automatic Instagram posting is NOT enabled, and the existing Brillio SuperProfile Reel remains a draft until media is attached and scheduled.

SuperProfile docs: https://superprofile.bio/mcp/docs
