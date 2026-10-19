"""Read-only 87-employer official-source coverage audit.

A watchlisted name is a target, not proof its careers portal was crawled.
Does not discover vacancies, mark expiry, publish, or modify jobs.json.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from discovery_v3_full_list import DEFAULTS
from discovery_v3_source_registry import EMPLOYERS

ROOT = Path(__file__).resolve().parents[1]
WATCHLIST = ROOT / "data" / "employer-watchlist-87.json"

ALIASES = {
    "Tata Consultancy Services (TCS)": "TCS",
    "Deloitte": "Deloitte South Asia",
    "PwC": "PwC India",
    "KPMG": "KPMG India",
}


def audit(watchlist, registry=EMPLOYERS, listing_adapters=DEFAULTS):
    by_name = {e.name: e for e in registry}
    names = [(category, name) for category, group in watchlist["categories"].items()
             for name in group]
    if len(names) != 87 or len({name for _, name in names}) != 87:
        raise ValueError("Expected exactly 87 distinct watchlisted employers")

    items = []
    for category, company in names:
        name = ALIASES.get(company, company)
        source = by_name.get(name)
        if name in listing_adapters and source:
            coverage = "partial_full_list_shadow"
        elif source:
            coverage = "official_portal_probe_only"
        else:
            coverage = "no_official_source_adapter"
        items.append({
            "company": company,
            "category": category,
            "mappedSource": name if source else None,
            "officialSource": source.url if source else None,
            "coverage": coverage,
            "publishCapable": False,
        })

    counts = {state: sum(x["coverage"] == state for x in items)
              for state in ("partial_full_list_shadow",
                            "official_portal_probe_only",
                            "no_official_source_adapter")}
    return {
        "mode": "coverage_audit_only",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "targetEmployers": 87,
        "registeredEmployers": 87 - counts["no_official_source_adapter"],
        "counts": counts,
        "all87CompletelySearched": False,
        "autoPublishEnabled": False,
        "notes": [
            "Full-list shadow is still page/region/time bounded and is not proof of complete coverage.",
            "Deloitte South Asia is represented; Deloitte USI needs its own source coverage.",
            "No employer is treated as expired merely because discovery did not find it.",
            "Add individually validated official endpoints and adapter coverage before enabling publication.",
        ],
        "items": items,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="")
    args = ap.parse_args()
    data = audit(json.loads(WATCHLIST.read_text(encoding="utf-8")))
    output = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
