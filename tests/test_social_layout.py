import unittest
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
PRIMARY = "https://whatsapp.com/channel/0029VbAxOna7NoZvhuKX362z"


class Links(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.links = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.append(dict(attrs))


class SocialLayoutTests(unittest.TestCase):
    def test_job_checker_placement(self):
        pages = list((ROOT / "jobs").glob("*.html"))
        self.assertTrue(pages)
        for page in pages:
            with self.subTest(page=page.name):
                text = page.read_text()
                self.assertEqual(text.count('id="resumeMatch"'), 1)
                self.assertLess(text.index('Job Overview'), text.index('id="resumeMatch"'))
                self.assertLess(text.index('id="resumeMatch"'), text.index('>Eligibility</h2>'))
                self.assertIn('href="#resumeMatch"', text)
                self.assertIn('scroll-margin-top:88px', text)
                self.assertIn('href="/telegram.html"', text)

    def test_primary_channel_only(self):
        for page in [ROOT / "index.html", ROOT / "contact.html", ROOT / "telegram.html", *list((ROOT / "jobs").glob("*.html"))]:
            text = page.read_text()
            for link in Links(text).links:
                if "whatsapp.com/channel/" in link.get("href", ""):
                    self.assertEqual(link["href"], PRIMARY)
        text = (ROOT / "index.html").read_text()
        self.assertNotIn("WhatsApp Channel 2", text)
        self.assertNotIn("WhatsApp 2", text)
        mobile = text.split('id="mobileMenu"', 1)[1].split("</header>", 1)[0]
        self.assertEqual(mobile.count(PRIMARY), 1)

    def test_telegram_fallback(self):
        text = (ROOT / "telegram.html").read_text()
        self.assertIn('href="tg://resolve?domain=HD_Careers"', text)
        self.assertIn('href="https://t.me/HD_Careers"', text)
        self.assertIn("navigator.clipboard.writeText('@HD_Careers')", text)
        self.assertIn('role="status"', text)


if __name__ == "__main__":
    unittest.main()
