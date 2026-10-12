import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from discovery_v3_full_list import listing_url, job_from_link, parse_page,scan_employer,process,page_size

class FakeFetcher:
    def __init__(self, responses):
        self.responses=responses
    def get(self,url,company):
        return self.responses.get(url,{"status":"unconfirmed","reason":"Missing fixture"})

def fixture(page=0,total=100):
    start=page*50+1
    end=min(total,(page+1)*50)
    pagecount=(total+49)//50
    rows=[]
    for n in range(start,end+1):
        location="Bangalore, IN" if n%2 else "London, UK"
        rows.append('<tr><td><a href="/job/Role-'+str(n)+'/'+
                    str(170000+n)+'-en_US/">Role '+str(n)+'</a></td><td>'+location+'</td></tr>')
    return ('<html>Results '+str(start)+' – '+str(end)+' of '+str(total)+
            ' Page '+str(page+1)+' of '+str(pagecount)+''.join(rows)+'</html>')

class WiproAdapterTests(unittest.TestCase):
    def test_50_jobs_per_page_and_official_locale(self):
        self.assertEqual(page_size("Wipro"),50)
        self.assertEqual(listing_url("Wipro",0),
                         "https://careers.wipro.com/viewalljobs/?locale=en_US")
        self.assertEqual(listing_url("Wipro",1),
                         "https://careers.wipro.com/viewalljobs/50/?locale=en_US")

    def test_parse_positive_india_evidence_only(self):
        result=parse_page("Wipro",fixture(0),listing_url("Wipro",0),0)
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["jobs"]),50)
        self.assertEqual(sum(j["country"]=="IN" for j in result["jobs"]),25)

    def test_complete_two_page_fixture(self):
        responses={listing_url("Wipro",i):{"status":"ok","body":fixture(i)} for i in range(2)}
        out=scan_employer("Wipro",FakeFetcher(responses),max_pages=2,pause=0)
        self.assertTrue(out["complete"])
        self.assertEqual(out["totalReported"],100)
        self.assertEqual(out["pagesRead"],2)
        summary=process([out],[],FakeFetcher({}),verify_new=0,pause=0)
        self.assertEqual(summary["discoveredNewIndia"],50)

    def test_incomplete_global_feed_never_proves_expiry(self):
        responses={listing_url("Wipro",0):{"status":"ok","body":fixture(0,total=120)}}
        out=scan_employer("Wipro",FakeFetcher(responses),max_pages=1,pause=0)
        self.assertFalse(out["complete"])
        self.assertEqual(out["status"],"partial")

    def test_wrong_host_rejected(self):
        job=job_from_link("Wipro","https://fake.example/job/SWE/175263-en_US/",
                          "Developer",listing_url("Wipro",0))
        self.assertIsNone(job)

if __name__=="__main__":
    unittest.main()
