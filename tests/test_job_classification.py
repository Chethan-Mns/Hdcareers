"""Classification contract: zero-year full-time is fresher; internships stay separate."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from job_classification import classified, experience_type, field_type
from select_auto_verified_jobs import publication_bucket


class JobClassificationTests(unittest.TestCase):
    def role(self,name,years,**kw):
        return {"company":"Sample","role":name,"expYears":years,"cat":"it","field":"it","expType":"fresher",**kw}

    def test_zero_years_fresher(self):
        for years in ("0 years","0-1 years","0–2 years","0 to 3 years","0+ years"):
            with self.subTest(years=years):
                self.assertEqual(experience_type(self.role("Software Developer",years)),"fresher")

    def test_required_positive_years_experienced(self):
        for years in ("1-2 years","1–2 years","2-4 years","1+ years","At least 2 years experience"):
            with self.subTest(years=years):
                self.assertEqual(experience_type(self.role("Software Developer",years)),"experienced")
                self.assertIsNone(publication_bucket(self.role("Software Developer",years)))

    def test_zero_in_multiple_paths(self):
        self.assertEqual(experience_type(self.role("AI Engineer","0 years with Master's; 2 years with Bachelor's")),"fresher")

    def test_support_sales_bpo_nonit_even_with_technical_skills(self):
        for title in ("Customer Support Engineer","Sales Associate","BPO Executive","Service Desk Analyst"):
            with self.subTest(title=title):
                job=self.role(title,"0-1 years",skills=["SQL","Python"])
                self.assertEqual(field_type(job),"nonit")
                self.assertIsNone(publication_bucket(job))
                job.update(cat="nonit",field="nonit")
                self.assertEqual(publication_bucket(job),"nonTechFullTime")

    def test_technical_analyst_it(self):
        self.assertEqual(field_type(self.role("Data Analyst","0-2 years",skills=["Python","SQL"])),"it")

    def test_training_never_fulltime(self):
        for cat,role in (("internship","Software Intern"),("apprenticeship","Design Apprenticeship")):
            for experience_type_label in ("fresher","internship/apprenticeship"):
                with self.subTest(cat=cat,experience=experience_type_label):
                    j=self.role(role,"0-1 years")
                    j.update(cat=cat,expType=experience_type_label)
                    self.assertEqual(classified(j)["cat"],cat)
                    self.assertEqual(publication_bucket(j),"internshipOrApprenticeship")

    def test_wrongly_labelled_internship_cannot_fill_it_quota(self):
        j=self.role("Software Engineering Intern","0-1 years")
        self.assertIsNone(publication_bucket(j))

    def test_legacy_role_page_display(self):
        import generate
        j=self.role("CAD Design Apprenticeship","2025 or 2026 graduates")
        j.update(cat="apprenticeship")
        result=classified(j)
        self.assertTrue(result["training"])
        self.assertEqual(result["cat"],"apprenticeship")


if __name__=="__main__":
    unittest.main()
