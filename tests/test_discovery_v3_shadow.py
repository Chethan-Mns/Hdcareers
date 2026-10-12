import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from discovery_v3_shadow import classify_exact, classify_listing_absence, extract_listed_jobs
class DiscoveryShadowTests(unittest.TestCase):
    def test_only_exact_requisition_with_apply_is_live(self):
        page="<html><body><h1>Associate Analyst - Tax</h1><p>Requisition ID: 1750731</p><a href='/apply'>Apply now »</a></body></html>"
        found=classify_exact(page,"https://careers.ey.com/ey/job/test/","1750731","Associate Analyst - Tax")
        self.assertEqual(found["state"],"live")
        self.assertEqual(classify_exact(page,"https://careers.ey.com/ey/job/test/","1111111","Associate Analyst - Tax")["state"],"unconfirmed")
        self.assertEqual(classify_exact(page.replace("Apply now »","Learn more"),"https://careers.ey.com/ey/job/test/","1750731","Associate Analyst - Tax")["state"],"unconfirmed")
    def test_not_expired_for_captcha_or_closed_text_without_corroboration(self):
        page="<h1>Job vacancy</h1> This job is no longer available"
        self.assertEqual(classify_exact(page,"https://careers.ey.com/ey/job/test/","1750731","Job vacancy")["state"],"unconfirmed")
    def test_listing_scrapes_only_exact_job_links(self):
        page='<a href="/ey/job/India-SW-Analyst/1445632533/">Software Analyst</a><a href="https://other.example/job/test/433829433/">Third Party</a><a href="/privacy">Privacy</a>'
        result=extract_listed_jobs(page,"https://careers.ey.com/ey/search/","careers.ey.com")
        self.assertEqual(list(result),["1445632533"])
    def test_missing_from_one_full_listing_is_not_expired(self):
        older={"status":"ok","complete":True,"employer":"EY","filter":"India","ids":["1750731"]}
        newer={"status":"ok","complete":True,"employer":"EY","filter":"India","ids":[]}
        self.assertEqual(classify_listing_absence(older,newer,"1750731"),"missing_once")
        newer["complete"]=False
        self.assertEqual(classify_listing_absence(older,newer,"1750731"),"unconfirmed")
        newer["complete"]=True
        newer["filter"]="Global"
        self.assertEqual(classify_listing_absence(older,newer,"1750731"),"unconfirmed")
if __name__=="__main__":unittest.main()
