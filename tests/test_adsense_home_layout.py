"""Prevent homepage and Insights SSR fallbacks from breaking their layouts."""
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class BalancedHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.errors.append((tag, self.stack[-1] if self.stack else None))
        else:
            self.stack.pop()


class HomepageFallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.jobs = json.loads((ROOT / "data/jobs.json").read_text(encoding="utf-8"))
        cls.active = [j for j in cls.jobs if j.get("status") == "active"]

    def section(self, label):
        start = '<section class="hdp-block" aria-labelledby="' + label + '">'
        pos = self.index.find(start)
        self.assertGreaterEqual(pos, 0, f"Missing {label}")
        end = self.index.find("</section>", pos)
        self.assertGreater(end, pos)
        return self.index[pos:end + len("</section>")]

    def test_recent_job_cards_stay_inside_the_grid(self):
        section = self.section("hdpRecentTitle")
        parser = BalancedHTML()
        parser.feed(section)
        self.assertEqual([], parser.errors, "Malformed nested HTML in recent jobs")
        self.assertEqual([], parser.stack, "Unclosed tags in recent jobs section")
        self.assertEqual(4, section.count('class="hdp-featured-item"'))
        self.assertEqual(4, section.count('<article class="hdp-featured-item">'))
        self.assertEqual(4, section.count("</article>"))
        self.assertTrue(section.endswith("</div></section>"))
        self.assertEqual(4, section.count('<div class="hdp-job-company">'))

    def test_featured_employers_stay_inside_the_grid(self):
        section = self.section("hdpCompaniesTitle")
        parser = BalancedHTML()
        parser.feed(section)
        self.assertEqual([], parser.errors)
        self.assertEqual([], parser.stack)
        self.assertEqual(4, section.count('class="hdp-company"'))
        self.assertTrue(section.endswith("</div></section>"))

    def test_meaningful_fallback_counters(self):
        employers = len({j["company"] for j in self.active if j.get("company")})
        self.assertIn(f'id="hdpJobs">{len(self.active)}</b>', self.index)
        self.assertIn(f'id="hdpEmployers">{employers}</b>', self.index)
        insights = (ROOT / "insights.html").read_text(encoding="utf-8")
        self.assertIn(f'id="hiActive">{len(self.active)}</strong>', insights)
        self.assertNotIn("Loading current city data…", insights)
        self.assertIn('id="hiCompanies" class="hi-company-gallery"', insights)
        self.assertIn('id="hiSkills" class="hi-skillwrap"', insights)


if __name__ == "__main__":
    unittest.main()
