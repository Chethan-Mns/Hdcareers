import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_job_availability import classify, check, require_active

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
        for code in (403, 404, 429, 500):
            self.assertEqual(classify(JOB, 'Job not found', JOB['apply'], code)[0], 'review')
        self.assertEqual(classify(JOB, 'Verify you are human', JOB['apply'])[0], 'review')
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

if __name__ == '__main__': unittest.main()
