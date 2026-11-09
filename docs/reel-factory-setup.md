# HD Careers — Daily Instagram Reel automation

The **HD Careers Daily Reel Factory** workflow runs at **7:00 PM IST** each day. It is active in **preview-first mode**; automated account posting is deliberately off until the owner's services are connected.

## Automatic operations
1. Read the current published job database and last official-source availability scan.
2. Select only a Fresher IT / Fresher Non-IT job with a confirmed ACTIVE scan within 36 hours. Ignore reviewed/uncertain/expired/stale jobs and jobs with existing Instagram posting receipts.
3. Prepare a 10–12 second script, caption with five hashtags, exact job link, and branded white Reel card.
4. If owner footage and ElevenLabs credentials are configured, render a 9:16 MP4 with the narration and the card over footage.
5. Store preview artifacts for owner download. Nothing is posted to Instagram until explicitly authorized.

## One-time setup
- Supply original or rights-cleared vertical footage as MP4/MOV under assets/reel-footage/ (or configure an external footage-sync step).
- In repository Settings → Secrets and variables → Actions add secrets ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID. Do not paste tokens into the repository.
- Open GitHub Actions → HD Careers Daily Reel Factory → Run workflow, leaving Publish=false. Review the MP4 artifact if generated.
- For Meta publishing, connect an Instagram Professional account authorized for API content publishing. Add repository secrets INSTAGRAM_ACCOUNT_ID, INSTAGRAM_ACCESS_TOKEN and BLOB_READ_WRITE_TOKEN (for a public Vercel Blob MP4 URL).
- Test once using workflow_dispatch, Publish=true. Confirm the actual Instagram media ID and its caption.
- Then, and only after testing, set the GitHub Actions repository variable HD_REELS_AUTOPUBLISH=true to permit the 7 PM scheduled run to publish automatically. Remove or set to false to disable.

Instagram API requires public HTTPS media and proper publishing permissions. The Reel workflow refuses to publish when job verification is stale or media/credentials are unavailable. GitHub scheduling can be delayed; it does not guarantee exact wall-clock posting times.

Files: .github/workflows/daily-instagram-reel.yml, scripts/reel_factory.py, scripts/reel_upload.mjs, scripts/instagram_reel_publish.py and data/reel-posts.json.
