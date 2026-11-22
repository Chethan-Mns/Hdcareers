#!/usr/bin/env python3
"""HD Careers automatic free narration.

Prefer Microsoft Edge Neerja Expressive Neural for natural Indian-English delivery. Edge Read Aloud
is an unofficial, best-effort endpoint (no uptime/usage guarantee). If blocked,
fall back to Google Translate Indian-English (gTTS), clearly labeled in metadata.
Do not claim the fallback is Neerja or ElevenLabs.
"""
from __future__ import annotations
import argparse
import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path

NEERJA="en-IN-NeerjaExpressiveNeural"
DEFAULT_PROVIDER="edge-neerja-expressive"
MAX_WORDS=45


def validate_script(text: str) -> str:
    text=" ".join(str(text).split())
    if not text or len(text.split()) > MAX_WORDS or len(text) > 360:
        raise ValueError("Reel voice script must contain 1-45 words and at most 360 characters")
    return text


async def _edge_speech(text: str, output: Path, rate: str) -> None:
    import edge_tts
    speech=edge_tts.Communicate(text, voice=NEERJA, rate=rate)
    async def collect():
        maker=edge_tts.SubMaker()
        word_timings=[]
        with output.open("wb") as fp:
            async for msg in speech.stream():
                if msg["type"]=="audio":
                    fp.write(msg["data"])
                elif msg["type"]=="WordBoundary":
                    maker.feed(msg)
                    word_timings.append({
                        "word":msg["text"],
                        "start":round(msg["offset"]/10_000_000,4),
                        "end":round((msg["offset"]+msg["duration"])/10_000_000,4)})
        if word_timings:
            output.with_suffix(".wordtimings.json").write_text(
                json.dumps(word_timings,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
            output.with_suffix(".srt").write_text(maker.get_srt(),encoding="utf8")
    await asyncio.wait_for(collect(), timeout=70)


def _gtts_speech(text: str, output: Path) -> None:
    from gtts import gTTS
    gTTS(text=text, lang="en", tld="co.in", slow=False).save(str(output))


def _probe_duration(path: Path) -> float:
    result=subprocess.check_output([
        "ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=nokey=1:noprint_wrappers=1",str(path)
    ],text=True,timeout=12)
    return float(result.strip())


def generate(text: str, output: str | Path, *, engine: str="auto",
             allow_fallback: bool=False, rate: str="-3%") -> dict:
    text=validate_script(text)
    output=Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    if engine not in ("auto","edge","gtts"):
        raise ValueError("Unknown voice engine")
    errors=[]
    selected=()
    if engine in ("auto","edge"):
        try:
            asyncio.run(_edge_speech(text,output,rate))
            selected=("edge-neerja-expressive",NEERJA)
        except Exception as exc:
            errors.append("Neerja synthesis unavailable: "+type(exc).__name__)
            if engine=="edge" or not allow_fallback:
                raise RuntimeError("; ".join(errors)) from None
    if not selected and engine in ("auto","gtts"):
        try:
            _gtts_speech(text,output)
            selected=("google-indian-english","Indian English (gTTS)")
        except Exception as exc:
            errors.append("Indian English fallback unavailable: "+type(exc).__name__)
            raise RuntimeError("; ".join(errors)) from None
    if not output.exists() or output.stat().st_size < 3000:
        raise RuntimeError("Voice generator returned missing or too-small audio")
    print("Narration synthesis completed with",selected[0],"("+str(output.stat().st_size)+" bytes)")
    duration=_probe_duration(output)
    if duration < 2 or duration > 28:
        raise RuntimeError("Generated voice duration out of bounds")
    return {"engine":selected[0],"voice":selected[1],
            "neerja_expressive_exact":selected[0]=="edge-neerja-expressive","speechma_preset_verified":False,"durationSeconds":round(duration,3),
            "text":text,"fallbackUsed":selected[0]!="edge-neerja-expressive"}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--text",default="")
    parser.add_argument("--text-file",default="")
    parser.add_argument("--output",default="artifacts/reel/voice.mp3")
    parser.add_argument("--engine",choices=("auto","edge","gtts"),default="auto")
    parser.add_argument("--no-fallback",action="store_true")
    parser.add_argument("--rate",default="-3%")
    args=parser.parse_args()
    text=Path(args.text_file).read_text(encoding="utf8").strip() if args.text_file else args.text
    result=generate(text,args.output,engine=args.engine,allow_fallback=not args.no_fallback,rate=args.rate)
    metadata=Path(args.output).with_suffix(".voice.json")
    metadata.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("Generated voice via",result["engine"],"duration",result["durationSeconds"])


if __name__=="__main__":
    main()
