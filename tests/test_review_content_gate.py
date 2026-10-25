import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CHECK=ROOT/"scripts/preflight_review_content.py"
def candidate(complete=True):
    job={"company":"Example","role":"Engineer","loc":"Bengaluru","elig":"Computer Science degree",
         "desc":"Software engineering role","apply":"https://example.com/jobs/123",
         "sourceName":"Example official careers","resp":["Build software"] if complete else []}
    return {"id":"123","company":"Example","role":"Engineer","apply":job["apply"],"job":job}
class ContentGateTests(unittest.TestCase):
    def run_gate(self,ready):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"batch.json"
            path.write_text(json.dumps({"batchId":"test","priority":[candidate(ready)],"backup":[]}))
            return subprocess.run([sys.executable,str(CHECK),str(path),"--require-complete"],capture_output=True,text=True)
    def test_complete_draft_passes(self):
        self.assertEqual(self.run_gate(True).returncode,0)
    def test_missing_responsibilities_blocks(self):
        result=self.run_gate(False)
        self.assertNotEqual(result.returncode,0)
        self.assertIn("Content gate blocked",result.stderr)

if __name__=="__main__":unittest.main()
