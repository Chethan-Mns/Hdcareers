import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from cryptography.fernet import Fernet
from superprofile_oauth import pack,unpack,refresh


class SuperProfileOAuthTests(unittest.TestCase):
    def test_encrypted_store_never_exposes_refresh_token(self):
        with tempfile.TemporaryDirectory() as dir:
            file=Path(dir)/"state.enc.json"
            key=Fernet.generate_key()
            pack({"client_id":"safe-example","refresh_token":"private-refresh-value",
                  "token_endpoint":"https://mcp.superprofile.bio/oauth/token"},key,file)
            self.assertNotIn("private-refresh-value",file.read_text())
            self.assertEqual(unpack(file,key)["refresh_token"],"private-refresh-value")
            with self.assertRaises(RuntimeError):
                unpack(file,Fernet.generate_key())

    def test_refresh_rotates_secret_and_writes_temp_access_token(self):
        key=Fernet.generate_key()
        with tempfile.TemporaryDirectory() as dir:
            store=Path(dir)/"token.enc.json"
            access=Path(dir)/"short-lived-access.txt"
            pack({"client_id":"ci-worker","refresh_token":"rotating-old",
                  "token_endpoint":"https://mcp.superprofile.bio/oauth/token"},key,store)
            def provider(url,form=None,*,form_unused=None,**kwargs):
                if form is None:return {"token_endpoint":"https://mcp.superprofile.bio/oauth/token"}
                self.assertEqual(form["refresh_token"],"rotating-old")
                return {"access_token":"access-token-only-in-temp-file","refresh_token":"rotating-new"}
            with patch("superprofile_oauth.req_json",side_effect=provider):
                refresh(store,access,key=key)
            self.assertEqual(unpack(store,key)["refresh_token"],"rotating-new")
            self.assertNotIn("rotating-new",store.read_text())
            self.assertEqual(access.read_text().strip(),"access-token-only-in-temp-file")


if __name__=="__main__":
    unittest.main()
