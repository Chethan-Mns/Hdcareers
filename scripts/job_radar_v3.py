#!/usr/bin/env python3
"""HD Careers Job Radar V3 SHADOW engine. No production writes or messaging."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from job_verifier_v2 import fetch_json, verify_url

SUPPORTED = frozenset({"greenhouse", "lever", "ashby"})
STRONG_CLOSED_CODES = frozenset({
    "workday.can_apply_false",
    "oracle_hcm.exact_requisition_closed",
    "successfactors.exact_job_unavailable",
    "smartrecruiters.explicit_inactive",
})
MIN_CLOSURE_INTERVAL = timedelta(minutes=15)
LIVE_TTL = timedelta(minutes=30)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def parsed_at(value: str | None) -> datetime | None:
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
        return d if d and d.tzinfo else None
    except (ValueError, TypeError):
        return None


def canonical_url(url: str) -> str:
    p = urlsplit(url)
    params = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
              if not k.lower().startswith("utm_") and k.lower() not in {"source", "ref", "src", "gh_src"}]
    return urlunsplit((p.scheme.lower(), (p.hostname or "").lower(), p.path.rstrip("/"), urlencode(params), ""))


def clean_tenant(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{2,80}", value):
        raise ValueError("Invalid ATS tenant")
    return value


def source_id(provider: str, tenant: str) -> str:
    return f"{provider}:{tenant.casefold()}"


def job_id(provider: str, tenant: str, requisition: str) -> str:
    return f"{provider}:{tenant.casefold()}:{str(requisition).casefold()}"


def make_job(provider: str, tenant: str, rid: str, title: str, url: str,
             location: str = "") -> dict:
    if not rid or not title or not url:
        raise ValueError("Missing exact job identity, title or link")
    if urlsplit(url).scheme != "https":
        raise ValueError("Job link must use HTTPS")
    return {"key": job_id(provider, tenant, rid), "provider": provider, "tenant": tenant,
            "requisitionId": rid, "title": str(title).strip(), "url": url,
            "location": str(location).strip(), "source": source_id(provider, tenant)}


def parse_inventory(provider: str, tenant: str, payload) -> list[dict]:
    """Convert public ATS inventory into exact-identity jobs. Never infer LIVE from this alone."""
    clean_tenant(tenant)
    if provider not in SUPPORTED:
        raise ValueError("Unsupported inventory provider")
    if provider == "greenhouse":
        if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
            raise ValueError("Incomplete Greenhouse inventory")
        raw = payload["jobs"]
    elif provider == "lever":
        if not isinstance(payload, list):
            raise ValueError("Incomplete Lever inventory")
        raw = payload
    else:
        if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
            raise ValueError("Incomplete Ashby inventory")
        raw = payload["jobs"]
    jobs = []
    seen = set()
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("Invalid inventory record")
        if provider == "greenhouse":
            rid = str(item.get("id") or "")
            title = item.get("title") or ""
            url = f"https://job-boards.greenhouse.io/{tenant}/jobs/{rid}"
            loc = item.get("location") or {}
            location = loc.get("name", "") if isinstance(loc, dict) else ""
        elif provider == "lever":
            rid = str(item.get("id") or "")
            title = item.get("text") or ""
            url = f"https://jobs.lever.co/{tenant}/{rid}"
            cats = item.get("categories") or {}
            location = cats.get("location", "") if isinstance(cats, dict) else ""
        else:
            if item.get("isListed") is False:
                continue
            url = str(item.get("jobUrl") or "")
            parsed = urlsplit(url)
            bits = [x for x in parsed.path.split("/") if x]
            if parsed.hostname != "jobs.ashbyhq.com" or len(bits) < 2 or bits[0].casefold() != tenant.casefold():
                raise ValueError("Ashby URL mismatches official tenant")
            rid = bits[1]
            title = item.get("title") or ""
            location = item.get("location") or ""
        job = make_job(provider, tenant, rid, title, url, location)
        if job["key"] not in seen:
            seen.add(job["key"])
            jobs.append(job)
    return jobs


def inventory_endpoint(provider: str, tenant: str) -> str:
    tenant = clean_tenant(tenant)
    return {
        "greenhouse": f"https://boards-api.greenhouse.io/v1/boards/{tenant}/jobs",
        "lever": f"https://api.lever.co/v0/postings/{tenant}?mode=json",
        "ashby": f"https://api.ashbyhq.com/posting-api/job-board/{tenant}",
    }[provider]


def collect_inventory(provider: str, tenant: str) -> dict:
    endpoint = inventory_endpoint(provider, tenant)
    try:
        status, final_url, _, payload = fetch_json(endpoint)
        if status != 200 or urlsplit(final_url).hostname != urlsplit(endpoint).hostname:
            raise ValueError("Source returned an unexpected status or endpoint")
        jobs = parse_inventory(provider, tenant, payload)
        return {"source": source_id(provider, tenant), "ok": True,
                "jobs": jobs, "reason": "provider_inventory_complete", "url": endpoint}
    except Exception as exc:
        return {"source": source_id(provider, tenant), "ok": False,
                "jobs": [], "reason": f"{type(exc).__name__}: {str(exc)[:140]}", "url": endpoint}


def state_template() -> dict:
    return {"schema": 1, "sources": {}, "jobs": {}, "updatedAt": None}


def load_state(path: Path) -> dict:
    if not path.exists():
        return state_template()
    state = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(state, dict) or state.get("schema") != 1:
        raise ValueError("Incompatible shadow snapshot")
    state.setdefault("sources", {})
    state.setdefault("jobs", {})
    return state


def ensure_history(state: dict, job: dict, observed: datetime) -> dict:
    key = job["key"]
    if key not in state["jobs"]:
        state["jobs"][key] = {"job": job, "firstSeen": iso(observed), "lastSeen": None,
                              "missingStreak": 0, "closedObservations": [],
                              "verification": "UNCONFIRMED", "lifecycle": "DISCOVERED",
                              "lastVerifiedLive": None, "lastVerification": None}
    state["jobs"][key]["job"] = job
    return state["jobs"][key]


def observe_snapshot(state: dict, snap: dict, observed: datetime) -> dict:
    """A source failure or implausible sudden drop cannot count jobs as missing."""
    sid = snap["source"]
    previous = state["sources"].get(sid, {})
    if not snap.get("ok"):
        return {"source": sid, "accepted": False, "reason": snap.get("reason", "failed"),
                "present": 0, "missing": 0}
    jobs = snap.get("jobs")
    if not isinstance(jobs, list) or any(x.get("source") != sid for x in jobs):
        return {"source": sid, "accepted": False, "reason": "invalid_source_inventory", "present": 0, "missing": 0}
    keys = {j["key"] for j in jobs}
    if len(keys) != len(jobs):
        return {"source": sid, "accepted": False, "reason": "duplicate_requisition_in_inventory", "present": 0, "missing": 0}
    previous_keys = set(previous.get("keys", []))
    if len(previous_keys) >= 5 and len(keys) * 2 < len(previous_keys):
        return {"source": sid, "accepted": False, "reason": "anomalous_inventory_drop", "present": len(keys), "missing": 0}
    for job in jobs:
        hist = ensure_history(state, job, observed)
        hist["lastSeen"] = iso(observed)
        hist["missingStreak"] = 0
        if hist["lifecycle"] == "CLOSURE_SUSPECTED":
            hist["lifecycle"] = "RECHECK_REQUIRED"
    # Use all historically seen jobs, not only the immediately prior successful snapshot.
    # Otherwise a job missing twice would have a streak of one forever.
    missing = {key for key, hist in state["jobs"].items()
               if hist["job"]["source"] == sid and hist.get("lastSeen") and key not in keys}
    for key in missing:
        hist = state["jobs"][key]
        hist["missingStreak"] = hist.get("missingStreak", 0) + 1
        if hist["lifecycle"] != "EXPIRED":
            hist["lifecycle"] = "CLOSURE_SUSPECTED"
            hist["verification"] = "UNCONFIRMED"
    state["sources"][sid] = {"keys": sorted(keys), "lastSuccessfulScan": iso(observed),
                             "lastCount": len(keys), "endpoint": snap.get("url")}
    state["updatedAt"] = iso(observed)
    return {"source": sid, "accepted": True, "reason": "complete_inventory",
            "present": len(keys), "missing": len(missing)}


def reliable_open(verdict: dict, job: dict) -> bool:
    if verdict.get("state") != "LIVE" or verdict.get("provider") != job["provider"]:
        return False
    if str(verdict.get("requisition_id", "")).casefold() != job["requisitionId"].casefold():
        return False
    return any(e.get("tier") == "A" and e.get("polarity") == "open"
               and e.get("identity_match") == "exact" for e in verdict.get("evidence", [])) and not any(
                   e.get("tier") == "A" and e.get("polarity") == "closed" for e in verdict.get("evidence", []))


def explicitly_closed(verdict: dict, job: dict) -> bool:
    if verdict.get("provider") != job["provider"]:
        return False
    if str(verdict.get("requisition_id", "")).casefold() != job["requisitionId"].casefold():
        return False
    strong = [e for e in verdict.get("evidence", [])
              if e.get("tier") == "A" and e.get("polarity") == "closed"
              and e.get("identity_match") == "exact" and e.get("code") in STRONG_CLOSED_CODES]
    conflict = any(e.get("tier") == "A" and e.get("polarity") == "open" for e in verdict.get("evidence", []))
    return bool(strong) and not conflict


def apply_verification(hist: dict, verdict: dict, observed: datetime, present: bool) -> str:
    """Never call missing, 403, 404 or stale evidence EXPIRED on its own."""
    hist["lastVerification"] = {"state": verdict.get("state", "UNCONFIRMED"),
                                 "reasons": verdict.get("reasons", []), "checkedAt": iso(observed)}
    if present and reliable_open(verdict, hist["job"]):
        hist["verification"] = "LIVE"
        hist["lastVerifiedLive"] = iso(observed)
        hist["closedObservations"] = []
        hist["lifecycle"] = "VERIFIED_LIVE"
    elif explicitly_closed(verdict, hist["job"]):
        if present:
            # Exact open inventory conflicts with an explicit closure API signal.
            # Escalate uncertainty rather than automatically expiring a listed vacancy.
            hist["verification"] = "UNCONFIRMED"
            hist["closedObservations"] = []
            hist["lifecycle"] = "RECHECK_REQUIRED"
            return hist["lifecycle"]
        observations = [t for t in hist.get("closedObservations", []) if parsed_at(t)]
        if not observations or observed - parsed_at(observations[-1]) >= MIN_CLOSURE_INTERVAL:
            observations.append(iso(observed))
        hist["closedObservations"] = observations[-3:]
        first = parsed_at(observations[0]) if observations else None
        if len(observations) >= 2 and first and observed - first >= MIN_CLOSURE_INTERVAL:
            hist["lifecycle"] = "EXPIRED"
            hist["verification"] = "EXPIRED"
        else:
            hist["lifecycle"] = "CLOSURE_SUSPECTED"
            hist["verification"] = "UNCONFIRMED"
    else:
        hist["verification"] = "UNCONFIRMED"
        hist["closedObservations"] = []
        if hist.get("missingStreak"):
            hist["lifecycle"] = "CLOSURE_SUSPECTED"
        else:
            hist["lifecycle"] = "RECHECK_REQUIRED"
    return hist["lifecycle"]


def eligible_for_publish(hist: dict, observed: datetime) -> bool:
    checked = parsed_at(hist.get("lastVerifiedLive"))
    source_last = parsed_at(hist.get("lastSeen"))
    return (hist.get("lifecycle") == "VERIFIED_LIVE"
            and hist.get("verification") == "LIVE"
            and checked is not None and timedelta(0) <= observed - checked <= LIVE_TTL
            and source_last is not None and timedelta(0) <= observed - source_last <= LIVE_TTL)


def select_top(state: dict, observed: datetime, count: int = 10) -> list[dict]:
    jobs = [x["job"] for x in state["jobs"].values() if eligible_for_publish(x, observed)]
    jobs.sort(key=lambda j: (priority(j), j["title"], j["key"]), reverse=True)
    selected = []
    per_tenant = defaultdict(int)
    for j in jobs:
        employer = j["tenant"].casefold()
        if per_tenant[employer] >= 2:
            continue
        selected.append(j)
        per_tenant[employer] += 1
        if len(selected) == count:
            break
    return selected


def priority(job: dict) -> int:
    # Role usefulness, not an assertion of eligibility: eligibility comes from the actual posting.
    role = job["title"].casefold()
    points = 0
    if any(t in role for t in ("intern", "graduate", "trainee", "associate", "entry level", "junior")):
        points += 40
    if any(t in role for t in ("software", "engineer", "developer", "data", "analyst")):
        points += 20
    if any(t in role for t in ("senior", "principal", "staff", "director", "manager")):
        points -= 25
    return points


def current_inventory_candidates(state: dict, successes: list[dict]) -> list[dict]:
    found = set()
    for s in successes:
        if s.get("accepted"):
            found.update(state["sources"][s["source"]]["keys"])
    return [state["jobs"][key]["job"] for key in sorted(found)]


def run_shadow(sources: list[dict], state: dict, observed: datetime,
               max_verify: int = 8, verifier=verify_url,
               snapshots: list[dict] | None = None) -> tuple[dict, dict]:
    sources = sources[:25]
    responses = snapshots if snapshots is not None else [collect_inventory(s["provider"], s["tenant"]) for s in sources]
    audits = [observe_snapshot(state, snapshot, observed) for snapshot in responses]
    jobs = current_inventory_candidates(state, audits)
    jobs.sort(key=lambda x: (priority(x), x["key"]), reverse=True)
    present_keys = {j["key"] for j in jobs}
    # Missing jobs have a dedicated small recheck budget; they cannot be auto-expired by disappearance.
    missing_jobs = [hist["job"] for hist in state["jobs"].values()
                    if hist["job"]["source"] in {a["source"] for a in audits if a.get("accepted")}
                    and hist["job"]["key"] not in present_keys and hist.get("missingStreak", 0) > 0]
    missing_jobs.sort(key=lambda j: j["key"])
    missing_budget = min(3, max_verify // 2)
    to_verify = [(j, False) for j in missing_jobs[:missing_budget]]
    to_verify.extend((j, True) for j in jobs[:max(0, max_verify - len(to_verify))])
    rechecks = []
    for job, present in to_verify:
        try:
            verdict = asdict(verifier(job["url"]))
        except Exception as exc:
            verdict = {"state": "UNCONFIRMED", "provider": job["provider"],
                       "requisition_id": job["requisitionId"], "reasons": [type(exc).__name__], "evidence": []}
        hist = state["jobs"][job["key"]]
        lifecycle = apply_verification(hist, verdict, observed, present=present)
        rechecks.append({"key": job["key"], "title": job["title"], "present": present,
                         "verifierState": verdict["state"], "lifecycle": lifecycle,
                         "eligible": eligible_for_publish(hist, observed)})
    report = {"shadow": True, "productionWrites": False, "websiteDeploy": False,
              "telegramPosts": False, "observedAt": iso(observed),
              "sourceAudits": audits, "discovered": len(jobs), "verified": len(rechecks),
              "suspectedClosures": len(missing_jobs),
              "topEligible": select_top(state, observed, 10),
              "lifecycleCounts": dict(Counter(h["lifecycle"] for h in state["jobs"].values())),
              "checks": rechecks, "noAutoExpireFromMissing": True}
    return state, report


def main():
    parser = argparse.ArgumentParser(description="SHADOW ONLY; no production changes or Telegram calls")
    parser.add_argument("--sources", default=str(ROOT / "config" / "autopilot-v3-sources.json"))
    parser.add_argument("--state", default="shadow-v3-state.json")
    parser.add_argument("--report", default="shadow-v3-report.json")
    parser.add_argument("--max-sources", type=int, default=4)
    parser.add_argument("--max-verify", type=int, default=6)
    args = parser.parse_args()
    config = json.loads(Path(args.sources).read_text(encoding="utf-8"))
    sources = config["sources"][:max(0, args.max_sources)]
    state, report = run_shadow(sources, load_state(Path(args.state)), utcnow(), max_verify=max(0, args.max_verify))
    Path(args.state).write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("V3 SHADOW SUMMARY", json.dumps({k: v for k, v in report.items() if k in
          {"discovered", "verified", "lifecycleCounts", "shadow", "productionWrites", "websiteDeploy", "telegramPosts"}}))
    print("SOURCES", json.dumps(report["sourceAudits"]))
    print("VERIFICATION", json.dumps(report["checks"]))
    print("TOP ELIGIBLE", json.dumps([j["key"] for j in report["topEligible"]]))


if __name__ == "__main__":
    main()
