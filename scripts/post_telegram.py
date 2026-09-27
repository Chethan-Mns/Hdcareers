from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "jobs.json"
SITE_BASE = "https://hdcareers.in/"
MAX_WAIT_SECONDS = 240
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


def load_current_jobs() -> list[dict]:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def load_event(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def jobs_from_dispatch(event: dict, current: list[dict]) -> list[dict]:
    incoming = event.get("client_payload", {}).get("jobs", [])
    if not isinstance(incoming, list):
        return []
    urls = {normalize_url(j.get("apply", "")) for j in incoming}
    pairs = {
        (str(j.get("company", "")).strip().lower(), str(j.get("role", "")).strip().lower())
        for j in incoming
    }
    return [
        job for job in current
        if normalize_url(job.get("apply", "")) in urls
        or (str(job.get("company", "")).strip().lower(), str(job.get("role", "")).strip().lower()) in pairs
    ]


def old_jobs_from_git(before: str) -> list[dict]:
    if not before or set(before) == {"0"}:
        return []
    result = subprocess.run(
        ["git", "show", f"{before}:data/jobs.json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []
    try:
        data = json.loads(result.stdout)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def jobs_from_push(event: dict, current: list[dict]) -> list[dict]:
    before = str(event.get("before", "") or "").strip()
    old = old_jobs_from_git(before)
    old_urls = {normalize_url(j.get("apply", "")) for j in old}
    old_pairs = {
        (str(j.get("company", "")).strip().lower(), str(j.get("role", "")).strip().lower())
        for j in old
    }
    added = []
    for job in current:
        url = normalize_url(job.get("apply", ""))
        pair = (str(job.get("company", "")).strip().lower(), str(job.get("role", "")).strip().lower())
        if url not in old_urls and pair not in old_pairs:
            added.append(job)
    return added


def jobs_for_event(event: dict, current: list[dict]) -> list[dict]:
    if isinstance(event.get("client_payload", {}).get("jobs"), list):
        return jobs_from_dispatch(event, current)
    if "before" in event:
        return jobs_from_push(event, current)
    return []


def compact_qualification(job: dict) -> str:
    explicit = str(job.get("qualification", "") or "").strip()
    if explicit:
        return explicit

    elig = re.sub(r"\s+", " ", str(job.get("elig", "") or "")).strip()
    if not elig:
        return "Refer official job eligibility"

    found = []
    for pattern in DEGREE_TERMS:
        for match in re.finditer(pattern, elig, flags=re.I):
            value = match.group(0).strip()
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
    return bool(batch and batch.lower() not in {"not specified", "n/a", "na"})


def should_include_package(job: dict) -> bool:
    salary = str(job.get("salary", "") or "").strip()
    return bool(salary and salary.lower() not in {"not disclosed", "not specified", "n/a", "na"})


def html_escape(value: str) -> str:
    return html.escape(str(value or ""), quote=False)


def message_for(job: dict) -> str:
    company = html_escape(job.get("company", "Company"))
    role = html_escape(job.get("role", ""))
    qualification = html_escape(compact_qualification(job))
    location = html_escape(job.get("loc", ""))

    lines = [
        f"{company} is Hiring ✅",
        "",
        f"<b>Role:</b> {role}",
    ]

    if should_include_batch(job):
        lines.append(f"<b>Batch:</b> {html_escape(job.get('batch', ''))}")

    lines.append(f"<b>Qualification:</b> {qualification}")

    if str(job.get("expType", "")).lower() == "experienced":
        exp = str(job.get("expYears", "") or "").strip()
        if exp and exp.lower() not in {"not specified", "n/a", "na"}:
            lines.append(f"<b>Experience:</b> {html_escape(exp)}")

    lines.append(f"<b>Location:</b> {location}")

    if should_include_package(job):
        lines.append(f"<b>Package:</b> {html_escape(job.get('salary', ''))}")

    page = str(job.get("page", "") or "").lstrip("/")
    apply_url = SITE_BASE + page if page else str(job.get("apply", "") or "")

    lines.extend([
        "",
        f"Apply Link: {html_escape(apply_url)}",
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
        "parse_mode": "HTML",
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

    event = load_event(sys.argv[1])
    current = load_current_jobs()
    jobs = jobs_for_event(event, current)
    if not jobs:
        print("No newly published jobs found for Telegram.")
        return

    first_page = str(jobs[0].get("page", "") or "")
    if not wait_for_live(first_page):
        raise SystemExit("HD Careers production page did not become live within the wait window. Telegram post skipped.")

    for job in jobs:
        send_telegram(token, channel, message_for(job))
        print(f"Posted to Telegram: {job.get('company')} — {job.get('role')}")


if __name__ == "__main__":
    main()
