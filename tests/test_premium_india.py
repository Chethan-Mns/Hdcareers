import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
class PremiumIndiaDashboardTests(unittest.TestCase):
    def test_home_uses_first_design_with_verified_data(self):
        home=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn('hdm-widget hdm-home',home)
        self.assertIn('id="hdpLocationMap"',home)
        self.assertIn('data-hdm-bars',home)
        self.assertIn('data-hdm-total',home)
        self.assertIn('data-hdm-cities',home)
        self.assertIn('assets/premium-india-v2.css',home)
        self.assertIn('assets/premium-india-v2.js',home)
        self.assertIn('assets/hd-map-lazy.js',home)
        self.assertNotIn('class="hdp-map-dashboard"',home)

    def test_insights_main_and_weekly_match_the_template(self):
        files=("assets/premium-insights-template.html","insights.html","insights/weekly-hiring-insights.html")
        for path in files:
            with self.subTest(path=path):
                html=(ROOT/path).read_text(encoding="utf-8")
                self.assertIn('hdm-widget hdm-insights',html)
                self.assertIn('data-hdm-ring',html)
                self.assertIn('data-hdm-citycards',html)
                self.assertIn('data-hdm-regions',html)
                self.assertIn('id="hiLocationMap"',html)
                self.assertIn('premium-india-v2.css',html)
                self.assertIn('premium-india-v2.js',html)
                self.assertIn('hd-map-lazy.js',html)
                self.assertNotIn('<script defer src="assets/india-state-paths.js"',html)
                self.assertIn('id="hiSkills"',html)
                self.assertIn('id="hiCompanies"',html)
                self.assertIn('class="hi-footer"',html)

    def test_counts_derive_from_public_snapshot_only(self):
        data=json.loads((ROOT/"data/insights-summary.json").read_text())
        cities=data["cityPins"]
        self.assertGreaterEqual(len(cities),1)
        self.assertTrue(all(isinstance(x["count"],int) and x["count"]>0 for x in cities))
        total=sum(x["count"] for x in cities)
        script=(ROOT/"assets/premium-india-v2.js").read_text()
        self.assertIn('total=pins.reduce',script)
        self.assertIn('const present=[...regionTotals]',script)
        self.assertIn('if(!total)return',script)
        self.assertGreaterEqual(total,1)
        self.assertNotIn("growthPercent",script)
        self.assertNotIn("lastMonth",script)

    def test_lazy_state_map_loads_both_pages(self):
        s=(ROOT/"assets/hd-map-lazy.js").read_text()
        self.assertIn('getElementById("hdpLocationMap")',s)
        self.assertIn('getElementById("hiLocationMap")',s)
        self.assertIn('document.body.dataset.prefix',s)
        self.assertIn("IntersectionObserver",s)
        self.assertNotIn("innerHTML",s)

    def test_only_map_sections_replaced(self):
        src=(ROOT/"assets/premium-insights-template.html").read_text()
        self.assertEqual(src.count('id="hiLocationMap"'),1)
        self.assertIn('> Skills in demand</h2>',src)
        self.assertIn('> Companies hiring on HD Careers</h2>',src)
        self.assertIn('> Experience distribution</h2>',src)
        self.assertIn('HD Careers (hdcareers.in)',src)

if __name__=="__main__":
    unittest.main()
