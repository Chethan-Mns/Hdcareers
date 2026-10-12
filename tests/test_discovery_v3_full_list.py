import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from discovery_v3_full_list import (
    DEFAULTS, normalized_url, listing_url, job_from_link, job_key,
    parse_page, scan_employer, consecutive_absence, process, verify_exact_listing_job
)


def page_html(company="EY", page=0, total=50, override=None):
    start = page * 25 + 1
    end = min(total, (page+1)*25)
    pages = (total+24)//25
    host = DEFAULTS[company]["host"]
    jobs = []
    for idx in range(start, end+1):
        title = f"Software Engineer {idx}"
        jobs.append(f'<a href="https://{host}/ey/job/City-Software-Engineer-{idx}/'
                    f'{1400000000+idx}/">{title}</a>')
    if override is not None:
        jobs = override
    return (f'<html>Results {start} – {end} of {total} Page {page+1} of {pages}'
            + "".join(jobs)+"</html>")


class FakeFetcher:
    def __init__(self, responses):
        self.responses = responses
        self.called = []

    def get(self, url, company):
        self.called.append((url, company))
        return self.responses.get(url, {"status":"unconfirmed", "reason":"Not in fixture"})


class FullListTests(unittest.TestCase):
    def test_pagination_uses_real_sap_startrow(self):
        self.assertIn("startrow=25", listing_url("EY",1))
        self.assertIn("/718244/50/", listing_url("Deloitte South Asia",2))
        self.assertIn("page=3", listing_url("HCLTech",3))

    def test_parse_one_page_requires_exact_count_and_range(self):
        r=parse_page("EY",page_html(),listing_url("EY",0),0)
        self.assertTrue(r["valid"])
        self.assertEqual(len(r["jobs"]),25)
        self.assertEqual(r["pages"],2)
        self.assertFalse(parse_page("EY",page_html(),listing_url("EY",0),1)["valid"])
        self.assertFalse(parse_page("EY","<html>Current openings are loading</html>",
                                    listing_url("EY",0),0)["valid"])

    def test_duplicate_or_missing_records_fail_closed(self):
        same = ['<a href="/ey/job/City-Test/1400000001/">Engineer</a>']*25
        r=parse_page("EY",page_html(override=same),listing_url("EY",0),0)
        self.assertFalse(r["valid"])
        self.assertEqual(len(r["jobs"]),1)

    def test_complete_scan_needs_every_page_and_matching_total(self):
        urls=[listing_url("EY",i) for i in range(2)]
        fetcher=FakeFetcher({urls[i]:{"status":"ok","body":page_html(page=i)}
                             for i in range(2)})
        r=scan_employer("EY",fetcher,max_pages=2,pause=0)
        self.assertTrue(r["complete"])
        self.assertEqual((len(r["jobs"]),r["totalReported"],r["pagesRead"]), (50,50,2))
        fetcher2=FakeFetcher({urls[0]:{"status":"ok","body":page_html(page=0)}})
        partial=scan_employer("EY",fetcher2,max_pages=1,pause=0)
        self.assertFalse(partial["complete"])
        self.assertEqual(partial["status"],"partial")

    def test_changed_page_total_and_overlap_fail_closed(self):
        urls=[listing_url("EY",i) for i in range(2)]
        fetcher=FakeFetcher({urls[0]:{"status":"ok","body":page_html(page=0)},
                             urls[1]:{"status":"ok","body":page_html(page=1,total=75)}})
        result=scan_employer("EY",fetcher,max_pages=3,pause=0)
        self.assertFalse(result["complete"])
        self.assertIn("changed",str(result["problems"]))

    def test_hcl_dynamic_shell_is_not_a_complete_listing(self):
        f=FakeFetcher({listing_url("HCLTech",0):{
            "status":"ok","body":"<html>Current Openings in India Loading ...</html>"}})
        r=scan_employer("HCLTech",f,max_pages=5,pause=0)
        self.assertFalse(r["complete"])
        self.assertEqual(r["status"],"partial")
        self.assertEqual(len(r["jobs"]),0)

    def test_listing_link_stable_canonical_key(self):
        url="https://careers.ey.com/ey/job/City-SWE/1445632533/"
        row=job_from_link("EY",url,"Software Engineer",listing_url("EY",0))
        self.assertEqual(row["listingUrlId"],"1445632533")
        self.assertEqual(row["id"],job_key("EY",url))
        self.assertIsNone(job_from_link("EY","https://fake.example/job/SWE/1445632533/",
                                        "Software Engineer",listing_url("EY",0)))

    def test_exact_employer_identity_not_http_200(self):
        job=job_from_link("EY","https://careers.ey.com/ey/job/City-SWE/1445632533/",
                          "Software Engineer",listing_url("EY",0))
        body='<html><link rel="canonical" href="'+job["jobUrl"]+'">' + \
             '<h1>Software Engineer</h1><a href="/apply">Apply Now</a></html>'
        self.assertEqual(verify_exact_listing_job(body,job)["state"],"live")
        self.assertEqual(verify_exact_listing_job(body.replace("/apply",""),job)["state"],"unconfirmed")
        self.assertEqual(verify_exact_listing_job(body.replace(job["jobUrl"],"https://careers.ey.com/ey/job/Other/1445632533/"),job)["state"],"unconfirmed")
        self.assertEqual(verify_exact_listing_job(body.replace("Software Engineer","Finance Manager"),job)["state"],"unconfirmed")

    def test_two_complete_absences_only_flag_not_auto_expiry(self):
        older={"employer":"EY","filter":"India","status":"ok","complete":True,"ids":["a","b"]}
        missing={"employer":"EY","filter":"India","status":"ok","complete":True,"ids":["b"]}
        self.assertEqual(consecutive_absence([older,missing], "EY", "a"),"unconfirmed")
        self.assertEqual(consecutive_absence([older,missing,missing], "EY", "a"),
                         "missing_twice_needs_closure_evidence")
        incomplete={**missing,"complete":False}
        self.assertEqual(consecutive_absence([older,missing,incomplete], "EY", "a"),"unconfirmed")

    def test_ey_only_uses_row_based_india_country_evidence(self):
        listing=page_html(total=2,override=[
            '<tr><td><a href="/ey/job/Mumbai-Analyst/1400000001/">Analyst</a></td><td>Mumbai, MH, IN, 400028</td></tr>',
            '<tr><td><a href="/ey/job/London-Consultant/1400000002/">Consultant</a></td><td>London, UK</td></tr>'
        ])
        result=parse_page("EY",listing,listing_url("EY",0),0)
        self.assertTrue(result["valid"])
        self.assertEqual([j["country"] for j in result["jobs"]],["IN","unconfirmed"])
        scan={"jobs":result["jobs"]}
        out=process([scan],[],FakeFetcher({}),verify_new=0,pause=0)
        self.assertEqual(out["discoveredNewIndia"],1)

    def test_published_duplicates_are_excluded(self):
        job=job_from_link("EY","https://careers.ey.com/ey/job/City-SWE/1445632533/",
                          "Software Engineer",listing_url("EY",0))
        scan={"jobs":[job]}
        f=FakeFetcher({})
        result=process([scan],[{"apply":job["jobUrl"],"company":"EY"}],f,verify_new=3,pause=0)
        self.assertEqual(result["discoveredNewIndia"],0)
        self.assertEqual(result["alreadyPublished"],1)
        self.assertEqual(len(f.called),0)


if __name__ == "__main__":
    unittest.main()
