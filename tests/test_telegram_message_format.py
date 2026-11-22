"""Regression tests for concise daily Telegram alerts."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from post_telegram import compact_qualification, message_for


class TelegramMessageFormatTests(unittest.TestCase):
    def test_combined_degree_is_not_repeated(self):
        self.assertEqual(
            compact_qualification({
                "qualification": "B.E./B.Tech / B.Tech / graduate / postgraduate"
            }),
            "B.E./B.Tech / Graduate/Postgraduate",
        )

    def test_many_eligible_degrees_are_summarized_without_inventing_any(self):
        self.assertEqual(
            compact_qualification({"qualification": "MCA/M.Tech/B.Tech/B.E./MBA/BCA"}),
            "MCA / M.Tech + more",
        )

    def test_unrecognized_degree_is_not_invented(self):
        self.assertEqual(
            compact_qualification({"elig": "Must have a degree in civil engineering or equivalent"}),
            "Must have a degree in civil engineering or equivalent",
        )

    def test_missing_eligibility_does_not_guess(self):
        self.assertEqual(compact_qualification({}), "See official eligibility")

    def test_one_blank_line_between_social_links(self):
        job = {
            "company": "Synopsys",
            "role": "CAD / Design Support Apprenticeship",
            "qualification": "B.E./B.Tech / B.Tech / graduate / postgraduate",
            "loc": "Noida, Uttar Pradesh, India",
            "expType": "fresher",
            "page": "jobs/synopsys-cad-design-support-apprenticeship.html",
        }
        message = message_for(job)
        self.assertIn("<b>Qualification:</b> B.E./B.Tech / Graduate/Postgraduate", message)
        self.assertIn(
            "𝗝𝗼𝗶𝗻 𝗢𝘂𝗿 𝗪𝗵𝗮𝘁𝘀𝗔𝗽𝗽: https://whatsapp.com/channel/0029VbAxOna7NoZvhuKX362z\n\n"
            "𝗝𝗼𝗶𝗻 𝗢𝘂𝗿 𝗧𝗲𝗹𝗲𝗴𝗿𝗮𝗺: https://t.me/HD_Careers",
            message,
        )
        self.assertIn(
            "Apply Link: https://hdcareers.in/jobs/synopsys-cad-design-support-apprenticeship.html",
            message,
        )


if __name__ == "__main__":
    unittest.main()
