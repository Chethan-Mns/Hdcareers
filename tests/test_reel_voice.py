"""Voice generation safety tests: exact script and provider disclosures."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import reel_voice

class FreeReelVoiceTests(unittest.TestCase):
    def test_rejects_empty_and_long_scripts(self):
        for value in ("", "word "*50):
            with self.assertRaises(ValueError):
                reel_voice.validate_script(value)
    def test_compacts_whitespace(self):
        self.assertEqual(reel_voice.validate_script("Brillio  is \n hiring"),"Brillio is hiring")
    def test_preferred_neerja_voice(self):
        self.assertEqual(reel_voice.NEERJA,"en-IN-NeerjaExpressiveNeural")
        self.assertEqual(reel_voice.DEFAULT_PROVIDER,"edge-neerja-expressive")
    def test_fallback_explicitly_disclosed(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            audio=Path(tmp)/"voice.mp3"
            def write_audio(*args):
                audio.write_bytes(b"audio"*900)
            with patch.object(reel_voice,"_edge_speech",side_effect=RuntimeError("403")), \
                 patch.object(reel_voice,"_gtts_speech",side_effect=write_audio), \
                 patch.object(reel_voice,"_probe_duration",return_value=9.3):
                info=reel_voice.generate("Brillio is hiring freshers",audio)
            self.assertEqual(info["engine"],"google-indian-english")
            self.assertTrue(info["fallbackUsed"])
            self.assertFalse(info["neerja_expressive_exact"])
    def test_no_unannounced_fallback(self):
        with patch.object(reel_voice,"_edge_speech",side_effect=RuntimeError("403")):
            with self.assertRaises(RuntimeError):
                reel_voice.generate("Brillio is hiring freshers","/tmp/never-used-voice.mp3",allow_fallback=False)

if __name__=="__main__":
    unittest.main()
