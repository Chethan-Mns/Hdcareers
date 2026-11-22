# HD Careers automatic free Reel narration

Status: implemented and verified in GitHub Actions on 22 November 2026.

- Primary engine: `edge-tts` using `en-IN-NeerjaNeural` (Indian-English female). This is not the exact Speechma Neerja Expressive preset, or ElevenLabs Tripti.
- Fallback engine if the Neerja endpoint fails: `gTTS` Indian-English (`en`, `co.in`). Output metadata records when a fallback is used.
- No paid ElevenLabs API key is needed for this voice path. The voice generator works from the script, without manual MP3 uploads.
- Scripts: `scripts/reel_voice.py`, integrated into `scripts/reel_factory.py`. The 7 PM IST Reel workflow installs voice dependencies automatically.
- Each selected confirmed-active job gets its own script and narration. The spoken ending is: `Comment below and I'll share the application link directly.`
- Free Brillio voice smoke workflow saves voice as an artifact and stores a compact copy under `.github/generated`.
- If no approved reusable MP4/MOV is available under `assets/reel-footage/`, narration can still be produced but no video is rendered or published.
- Instagram publishing and SuperProfile comment-to-DM remain separate, opt-in, permissioned steps.

## Reliability and rights

The primary free Neerja engine is a community client of Microsoft's consumer Edge Read Aloud endpoint, not a supported public production API. It may stop working, and its availability or licensing for monetized promotional use is not guaranteed. The fallback uses Google Translate's unofficial TTS endpoint and also has no SLA. For long-term commercial automated posting, an official Azure Speech F0 resource may be preferable (free allowance, credentials required). Do not publish an unreviewed fallback voice as if it were Neerja.
