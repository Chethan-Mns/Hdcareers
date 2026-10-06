import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_job_availability import classify, check, require_active, prune_unverified_new_jobs, official_inventory_probe

JOB = {'id': 1, 'role': 'Data Engineer', 'company': 'Example', 'apply': 'https://careers.example.com/jobs/123', 'status': 'active'}

class AvailabilityTests(unittest.TestCase):
    def test_active_requires_role_and_apply(self):
        self.assertEqual(classify(JOB, '<h1>Data Engineer</h1><a>Apply now</a>', JOB['apply'])[0], 'active')
        self.assertEqual(classify(JOB, '<h1>Data Engineer</h1>', JOB['apply'])[0], 'review')
    def test_explicit_closure(self):
        self.assertEqual(classify(JOB, 'This job is no longer available', JOB['apply'])[0], 'expired')
    def test_hidden_template_not_closure(self):
        self.assertEqual(classify(JOB, '<script>This job is no longer available</script><h1>Data Engineer</h1>Apply now', JOB['apply'])[0], 'active')
    def test_redirect_never_active(self):
        self.assertEqual(classify(JOB, 'Data Engineer Apply now', 'https://careers.example.com/')[0], 'review')
    def test_access_errors_not_expired(self):
        for code in (403, 404, 410, 429, 500):
            self.assertEqual(classify(JOB, 'Job not found', JOB['apply'], code)[0], 'review')
        self.assertEqual(classify(JOB, 'Verify you are human', JOB['apply'])[0], 'review')
    def test_greenhouse_inventory_can_confirm_live_job(self):
        job = dict(JOB, apply='https://boards.greenhouse.io/acme/jobs/12345')
        with patch('check_job_availability.fetch_json', return_value={'id': 12345, 'title': 'Data Engineer'}):
            self.assertEqual(official_inventory_probe(job)[0], 'active')

    def test_lever_inventory_can_confirm_live_job(self):
        job = dict(JOB, apply='https://jobs.lever.co/acme/abc-123')
        with patch('check_job_availability.fetch_json', return_value={'id': 'abc-123', 'text': 'Data Engineer'}):
            self.assertEqual(official_inventory_probe(job)[0], 'active')

    def test_smartrecruiters_inventory_can_confirm_live_job(self):
        job = dict(JOB, apply='https://jobs.smartrecruiters.com/acme/744000123456789-data-engineer')
        with patch('check_job_availability.fetch_json', return_value={'id': '744000123456789-data-engineer', 'active': True}):
            self.assertEqual(official_inventory_probe(job)[0], 'active')

    def test_ashby_inventory_can_confirm_live_job(self):
        job = dict(JOB, apply='https://jobs.ashbyhq.com/acme/abc-123')
        payload = {'jobs': [{'title': 'Data Engineer', 'jobUrl': 'https://jobs.ashbyhq.com/acme/abc-123', 'applyUrl': 'https://jobs.ashbyhq.com/acme/abc-123/application'}]}
        with patch('check_job_availability.fetch_json', return_value=payload):
            self.assertEqual(official_inventory_probe(job)[0], 'active')

    def test_jobposting_jsonld_can_confirm_live_job(self):
        body = '<script type="application/ld+json">{"@type":"JobPosting","title":"Data Engineer","identifier":"REQ-123","validThrough":"2099-12-31T23:59:59Z"}</script>'
        self.assertEqual(classify(JOB, body, JOB['apply'])[0], 'active')

    def test_jobposting_jsonld_past_deadline_expires_job(self):
        body = '<script type="application/ld+json">{"@type":"JobPosting","title":"Data Engineer","identifier":"REQ-123","validThrough":"2020-01-01T00:00:00Z"}</script>'
        self.assertEqual(classify(JOB, body, JOB['apply'])[0], 'expired')

    def test_deadline(self):
        job = dict(JOB, closingAt='2026-09-29T18:00:00+05:30')
        now = datetime(2026, 9, 29, 12, 30, tzinfo=timezone.utc)
        self.assertEqual(check(job, now)['state'], 'expired')
    def test_invalid_deadline_not_expired(self):
        self.assertEqual(check(dict(JOB, closingAt='2026-09-29'))['state'], 'review')
    def test_network_failure(self):
        with patch('check_job_availability.safe_url', side_effect=TimeoutError):
            self.assertEqual(check(JOB)['state'], 'review')
    def test_publish_fails_closed(self):
        with patch('check_job_availability.check', return_value={'state': 'review', 'reason': 'Unknown'}):
            with self.assertRaises(SystemExit): require_active(JOB)
        with self.assertRaises(SystemExit): require_active(dict(JOB, status='expired'))

    def test_partial_batch_prunes_only_new_unverified_jobs(self):
        old = [dict(JOB, id=1)]
        jobs = [dict(JOB, id=1), dict(JOB, id=2), dict(JOB, id=3)]
        results = [
            {'id': 2, 'state': 'active'},
            {'id': 3, 'state': 'review'},
        ]
        kept, pruned, removed = prune_unverified_new_jobs(jobs, old, results)
        self.assertEqual([j['id'] for j in kept], [1, 2])
        self.assertEqual(pruned, [3])
        self.assertEqual([j['id'] for j in removed], [3])

    def test_partial_batch_does_not_prune_existing_jobs(self):
        old = [dict(JOB, id=1)]
        jobs = [dict(JOB, id=1)]
        results = [{'id': 1, 'state': 'review'}]
        kept, pruned, removed = prune_unverified_new_jobs(jobs, old, results)
        self.assertEqual([j['id'] for j in kept], [1])
        self.assertEqual(pruned, [])
        self.assertEqual(removed, [])

if __name__ == '__main__': unittest.main()
