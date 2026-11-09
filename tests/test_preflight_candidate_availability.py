import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from preflight_candidate_availability import label
class AvailabilityTests(unittest.TestCase):
    def test_closed(self):self.assertEqual(label({"state":"expired"}),"source-closed")
    def test_active(self):self.assertEqual(label({"state":"active"}),"source-active")
    def test_http_error_is_unsure(self):self.assertEqual(label({"state":"review","reason":"HTTP 404"}),"unsure")
if __name__=="__main__":unittest.main()
