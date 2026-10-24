"""Install the AdSense publisher verification tag on HD Careers public pages.

Preserves all existing markup. Excludes admin, API and draft templates.
Run after site generation so subsequent scheduled publishing retains the tag.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER_ID = "ca-pub-2038097288194658"
CODE = (
    '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client='
    + PUBLISHER_ID
    + '" crossorigin="anonymous"></script>'
)

def public_html_files():
    for folder in (ROOT, ROOT / "jobs", ROOT / "insights", ROOT / "resources"):
        if folder.is_dir():
            yield from sorted(folder.glob("*.html"))

def install(dry_run=False):
    installed = []
    for path in public_html_files():
        text = path.read_text(encoding="utf-8")
        if "<head" not in text.lower() or "</head>" not in text.lower():
            continue
        if "pagead2.googlesyndication.com/pagead/js/adsbygoogle.js" in text:
            if PUBLISHER_ID not in text:
                raise ValueError("Different AdSense publisher tag already on " + str(path))
            if text.count(PUBLISHER_ID) > 1:
                raise ValueError("Duplicate AdSense publisher tag on " + str(path))
            continue
        # Exact publisher code in the document head, once per HTML file.
        pos = text.lower().find("</head>")
        new_text = text[:pos] + CODE + "\n" + text[pos:]
        if not dry_run:
            path.write_text(new_text, encoding="utf-8")
        installed.append(str(path.relative_to(ROOT)))
    return installed

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    updates = install(args.dry_run)
    print(f"{'Would tag' if args.dry_run else 'Tagged'} {len(updates)} public HTML pages")
