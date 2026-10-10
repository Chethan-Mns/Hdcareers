# Cinematic Instagram Reel — SHADOW prototype

**Do not merge to main until the HD Careers Owner approves the final video.** This branch contains only an isolated demo of a 15-second 9:16, 1080×1920 MP4 for one verified published HD Careers job.

## Verified job / content

- Job record `data/jobs.json` ID 112: Accenture — AI/ML Computational Science Associate.
- Official employer job reference: `AIOC-S01665344`.
- HD Careers URL: `https://hdcareers.in/jobs/accenture-ai-ml-computational-science-associate-bengaluru-aioc-s01665344.html`
- Employment eligibility: BE/BTech, 0–1 years, Bengaluru.
- Published record marked active, with manual live verification on 10 October 2026. The official Accenture page had an Apply for this job control when checked during prototype preparation.
- **Salary not disclosed.** The generated Reel never fabricates a package.
- This first demo is deliberately locked to this single verified job. Do not remove the lock and auto-post arbitrary unverified listings.

## What it creates

`python scripts/reels/render_cinematic.py --job-id 112`

Produces `reel-shadow/output/reel-112.mp4` (15 seconds, H.264/AAC), cover JPG, standalone SRT subtitle file, voiceover script, caption TXT, and metadata JSON.

- Background: original procedurally animated nighttime city fallback, or a licensed b-roll file supplied as `--background PATH`.
- The shadow workflow tries a licensed **CC BY 3.0** city time-lapse from Wikimedia Commons: [City skyline (time lapse)](https://commons.wikimedia.org/wiki/File:City_skyline_(time_lapse).webm) by YouTube user Editor, https://creativecommons.org/licenses/by/3.0/. The generated caption includes attribution and identifies the adaptation when the video is used. It is generic B-roll, **not footage of Bengaluru**.
- Narration: offline `espeak` voice as a **temporary proof-of-concept**, not a premium neural AI voice. A licensed voice provider needs configuration and approval for the final design.
- Written subtitles are timed in three 5-second segments and also shown visually in each scene.
- Accurate stored Accenture icon from `data/jobs.json.logoPath` is rendered in the brand card when present.
- Fixed call to action: **Comment LINK**, with the actual HD Careers job-page URL for manual entry in SuperProfile.
- Nothing is posted to Instagram and no Instagram/Meta credentials or webhook are used.

## Preview

Open `/admin/reel-shadow.html` on the development-branch Vercel preview when the Vercel free-plan deployment limit allows. After the authenticated admin session is confirmed the page shows the MP4, cover download, subtitles, caption/script copy, and the HD Careers job URL.

The `Cinematic Reel shadow prototype` GitHub workflow generates, validates and commits preview assets to **this development branch only**. It also uploads a downloadable workflow artifact. Changes to `reel-shadow/output` do not retrigger the generator. It will not touch `main`.

If Vercel preview deployment is rate-limited, the owner may download the MP4 from the linked GitHub Actions workflow artifact or from the provided local prototype. Neither workaround implies the Admin Preview has deployed.

## Next implementation after approval

1. Replace the placeholder TTS with a configured, licensed natural AI voice; refine subtitle sync to phrase/word alignment.
2. Establish a license-vetted cinematic footage library with usage metadata and background selection by job category.
3. Rank one candidate per 10 **successfully published and live-verified** batch jobs, storing unique job ID and Reel status to prevent duplicates.
4. Persist MP4 and captions to an external media store (not Git commits) with retention and a signed Owner-only preview/download endpoint.
5. Keep Reel publishing manual and keep SuperProfile Auto DM configuration manual, per Owner decision. No direct Instagram publishing.

## Safety / production isolation

- Generated files, workflow commits and preview page stay only on `feature/cinematic-reel-shadow-20261010` until Owner approval.
- The video generator fails closed for inactive jobs, missing official apply URLs, and an unexpected job ID.
- The static preview page checks the admin session before displaying the media but its underlying static files are not a private storage boundary. Use private blob storage and signed access before uploading actual confidential assets in production.
