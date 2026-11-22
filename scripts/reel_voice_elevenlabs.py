#!/usr/bin/env python3
"""Generate the HD Careers Sarah narration WITH exact spoken-word timing.

Uses the owner's authorized ElevenLabs account. Do not publish promotional
content from an ElevenLabs free plan without confirmed commercial rights.
"""
from __future__ import annotations
import base64
import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SARAH_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"
MODEL_ID = "eleven_flash_v2_5"


def word_alignment(alignment: dict, expected_text: str) -> list[dict]:
    chars = alignment.get("characters") or []
    starts = alignment.get("character_start_times_seconds") or []
    ends = alignment.get("character_end_times_seconds") or []
    if len(chars) != len(starts) or len(starts) != len(ends) or not chars:
        raise ValueError("ElevenLabs alignment missing or incomplete")
    joined = "".join(chars)
    def normalized(s):
        return re.sub(r"[^\w]", "", str(s), flags=re.UNICODE).casefold()
    if normalized(joined) != normalized(expected_text):
        raise ValueError("ElevenLabs alignment does not match original script")
    result = []
    for match in re.finditer(r"\S+", joined):
        a,b = match.span()
        start,end = float(starts[a]),float(ends[b-1])
        if end <= start or start < 0 or (result and start < result[-1]["start"]):
            raise ValueError("Invalid or nonmonotonic ElevenLabs timestamp")
        result.append({"text": match.group(), "start": round(start,4), "end": round(end,4)})
    if len(result) < 7 or result[-1]["end"] > 30:
        raise ValueError("Narration length outside safe range")
    return result


def generate(text: str, output: str | Path, *, voice_id: str | None = None) -> dict:
    key = os.getenv("ELEVENLABS_API_KEY","").strip()
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY not configured; no synthetic voice fallback")
    text = " ".join(str(text).split())
    if not text or len(text.split()) > 45 or len(text) > 340:
        raise ValueError("Reel narration must be 1-45 words, up to 340 characters")
    voice_id = voice_id or os.getenv("ELEVENLABS_REEL_VOICE_ID") or SARAH_VOICE_ID
    if not re.fullmatch(r"[A-Za-z0-9]{15,40}", voice_id):
        raise ValueError("Invalid ElevenLabs voice id")
    request=Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps?output_format=mp3_44100_128",
        data=json.dumps({"text":text,"model_id":MODEL_ID}).encode("utf-8"),
        method="POST", headers={
            "xi-api-key":key,
            "Content-Type":"application/json",
            "Accept":"application/json",
        })
    try:
        with urlopen(request, timeout=75) as response:
            payload=json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"ElevenLabs voice API HTTP {exc.code}; no Reel rendered") from None
    except URLError as exc:
        raise RuntimeError("ElevenLabs voice API unreachable") from None
    words=word_alignment(payload.get("alignment") or payload.get("normalized_alignment") or {},text)
    try:
        audio=base64.b64decode(payload.get("audio_base64") or "", validate=True)
    except Exception:
        raise RuntimeError("ElevenLabs returned corrupt audio") from None
    if len(audio) < 3000:
        raise RuntimeError("ElevenLabs returned no MP3")
    output=Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(audio)
    timing=output.with_suffix(".wordtimings.json")
    timing.write_text(json.dumps(words,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    metadata={"provider":"elevenlabs","voice":"Sarah" if voice_id==SARAH_VOICE_ID else "configured ElevenLabs voice",
              "voiceId":voice_id,"model":MODEL_ID,
              "wordCount":len(words),"lastWordSeconds":words[-1]["end"],
              "commercialRightsVerified":os.getenv("HD_REEL_AUDIO_COMMERCIAL_LICENSE_CONFIRMED","false").lower()=="true"}
    output.with_suffix(".voice.json").write_text(json.dumps(metadata,indent=2)+"\n",encoding="utf-8")
    return metadata
