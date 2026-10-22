import json,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]
class SiteSpeedTest(unittest.TestCase):
 def test_home_has_static_css_and_map_lazy_loader(self):
  s=(P/"index.html").read_text();self.assertNotIn("cdn.tailwindcss.com",s);self.assertIn('assets/tailwind-built.css',s);self.assertIn('assets/hd-map-lazy.js',s);self.assertIn('class="hdp-block hdp-map-block hdm-widget hdm-home"',s);self.assertIn('assets/premium-india-v2.js',s)
 def test_generated_pages_static_css(self):
  self.assertNotIn("cdn.tailwindcss.com",(P/"generate.py").read_text())
 def test_curated_companies_and_logo(self):
  s=(P/"assets/premium-home.js").read_text();self.assertIn('["Deloitte","EY","Amazon","Accenture"]',s)
  j=json.loads((P/"data/approved-company-logos.json").read_text());self.assertTrue((P/j["EdgeVerve Systems"]).is_file())
