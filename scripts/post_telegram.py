from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "jobs.json"
SITE_BASE = "https://hdcareers.in/"
MAX_WAIT_SECONDS = 180
POLL_SECONDS = 10

DEGREE_TERMS = [
    r"B\.?E\.?\s*/?\s*B\.?Tech",
    r"B\.?Tech",
    r"M\.?Tech",
    r"MCA",
    r"BCA",
    r"MBA",
    r"BSc",
    r"MSc",
    r"Diploma",
    r"Bachelor(?:'s)? degree",
    r"Master(?:'s)? degree",
    r"Graduate",
    r"Postgraduate",
]


def normalize_url(value: str) -> str:
    return str(value or "").strip().rstrip("/").lower()


def load_event(path: str) -> list[dict]:
    event = json.loads(Path(path).read_text(encoding="utf-8"))
    jobs = event.get("client_payload", {}).get("jobs", [])
    return jobs if isinstance(jobs, list) else []


def match_published_jobs(incoming: list[dict]) -> list[dict]:
    current = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    urls = {normalize_url(j.get("apply", "")) for j in incoming}
    pairs = {
        (str(j.get("company", "")).strip().lower(), str(j.get("role", "")).strip().lower())
        for j in incoming
    }
    matched = []
    for job in current:
        pair = (str(job.get("company", "")).strip().lower(), str(job.get("role", "")).strip().lower())
        if normalize_url(job.get("apply", "")) in urls or pair in pairs:
            matched.append(job)
    return matched


def compact_qualification(job: dict) -> str:
    explicit = str(job.get("qualification", "") or "").strip()
    if explicit:
        return explicit

    elig = re.sub(r"\s+", " ", str(job.get("elig", "") or "")).strip()
    if not elig:
        return "See official eligibility"

    found = []
    for pattern in DEGREE_TERMS:
        for m in re.finditer(pattern, elig, flags=re.I):
            value = m.group(0).strip()
            if value.lower() not in {x.lower() for x in found}:
                found.append(value)
    if found:
        return " / ".join(found[:4])

    first = re.split(r"[•.;]|\s+-\s+", elig, maxsplit=1)[0].strip()
    return (first or elig)[:140].rstrip()


def should_include_batch(job: dict) -> bool:
    if str(job.get("expType", "")).lower() != "fresher":
        return False
    batch = str(job.get("batch", "") or "").strip()
    return bool(batch and batch.lower() not in {"not specified", "n/a", "na", "any"})


def should_include_package(job: dict) -> bool:
    salary = str(job.get("salary", "") or "").strip()
    return bool(salary and salary.lower() not in {"not disclosed", "not specified", "n/a", "na"})


def markdown_escape(value: str) -> str:
    text = str(value or "")
    for ch in ("\\", "_", "*", "[", "]", "(", ")"):
        text = text.replace(ch, "\\" + ch)
    text = text.replace(chr(96), "\\" + chr(96))
    return text


def message_for(job: dict) -> str:
    company = markdown_escape(job.get("company", "Company"))
    role = markdown_escape(job.get("role", ""))
    qualification = markdown_escape(compact_qualification(job))
    location = markdown_escape(job.get("loc", ""))

    lines = [
        f"{company} is Hiring ✅",
        "",
        f"*Role:* {role}",
    ]

    if should_include_batch(job):
        lines.append(f"*Batch:* {markdown_escape(job.get('batch', ''))}")

    lines.append(f"*Qualification:* {qualification}")

    if str(job.get("expType", "")).lower() == "experienced":
        exp = str(job.get("expYears", "") or "").strip()
        if exp and exp.lower() not in {"not specified", "n/a", "na"}:
            lines.append(f"*Experience:* {markdown_escape(exp)}")

    lines.append(f"*Location:* {location}")

    if should_include_package(job):
        lines.append(f"*Package:* {markdown_escape(job.get('salary', ''))}")

    page = str(job.get("page", "") or "").lstrip("/")
    apply_url = SITE_BASE + page if page else str(job.get("apply", "") or "")

    lines.extend([
        "",
        f"Apply Link: {apply_url}",
        "",
        "𝗝𝗼𝗶𝗻 𝗢𝘂𝗿 𝗪𝗵𝗮𝘁𝘀𝗔𝗽𝗽: https://whatsapp.com/channel/0029VbAxOna7NoZvhuKX362z",
        "𝗝𝗼𝗶𝗻 𝗢𝘂𝗿 𝗧𝗲𝗹𝗲𝗴𝗿𝗮𝗺: https://t.me/HD_Careers",
    ])
    return "\n".join(lines)


def wait_for_live(page: str) -> bool:
    if not page:
        return True
    url = SITE_BASE + str(page).lstrip("/")
    deadline = time.time() + MAX_WAIT_SECONDS
    while time.time() < deadline:
        try:
            req = Request(url, method="GET", headers={"User-Agent": "HD-Careers-Telegram-Publisher/1.0"})
            with urlopen(req, timeout=15) as res:
                if 200 <= res.status < 400:
                    return True
        except Exception:
            pass
        time.sleep(POLL_SECONDS)
    return False


def send_telegram(token: str, channel: str, text: str) -> None:
    endpoint = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urlencode({
        "chat_id": channel,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": "false",
    }).encode("utf-8")

    req = Request(endpoint, data=payload, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urlopen(req, timeout=30) as res:
            body = json.loads(res.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telegram HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Telegram network error: {exc}") from exc

    if not body.get("ok"):
        raise RuntimeError("Telegram API rejected the message: " + json.dumps(body))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: post_telegram.py <github-event-path>")

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    channel = os.environ.get("TELEGRAM_CHANNEL_ID", "").strip()
    if not token or not channel:
        print("Telegram secrets are not configured in GitHub Actions. Skipping channel post.")
        return

    incoming = load_event(sys.argv[1])
    jobs = match_published_jobs(incoming)
    if not jobs:
        raise SystemExit("No published jobs matched the repository_dispatch payload.")

    first_page = str(jobs[0].get("page", "") or "")
    if not wait_for_live(first_page):
        raise SystemExit("HD Careers production page did not become live within the wait window. Telegram post skipped.")

    for job in reversed(jobs):
        send_telegram(token, channel, message_for(job))
        print(f"Posted to Telegram: {job.get('company')} — {job.get('role')}")


if __name__ == "__main__":
    main()
