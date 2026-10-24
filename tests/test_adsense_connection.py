"""Guard AdSense site ownership snippet against duplication and admin leakage."""
import unittest
from pathlib import Path
from scripts.adsense_install import CODE, PUBLISHER_ID, ROOT, public_html_files, install

class AdSenseConnectionTests(unittest.TestCase):
    def test_publisher_code_present_once_inside_head(self):
        html=list(public_html_files())
        self.assertGreater(len(html), 150)
        self.assertTrue((ROOT/"index.html") in html)
        for f in html:
            data=f.read_text(encoding="utf-8")
            if "</head>" not in data.lower():
                continue
            with self.subTest(page=str(f.relative_to(ROOT))):
                self.assertEqual(1,data.count(PUBLISHER_ID))
                self.assertEqual(1,data.count(CODE))
                self.assertLess(data.index(CODE), data.lower().index("</head>"))

    def test_idempotent(self):
        self.assertEqual([], install(dry_run=True))

    def test_no_admin_pages_touched(self):
        self.assertFalse(any("admin" in p.relative_to(ROOT).parts for p in public_html_files()))

if __name__ == "__main__":
    unittest.main()
