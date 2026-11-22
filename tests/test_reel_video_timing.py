import sys
import json
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from reel_video import _ass_time, create_ass
from reel_voice_elevenlabs import SARAH_VOICE_ID, word_alignment


class ReelTimingTests(unittest.TestCase):
    def test_sarah_is_the_selected_approved_voice(self):
        self.assertEqual(SARAH_VOICE_ID, "EXAVITQu4vr4xnSDxMaL")

    def test_alignment_uses_real_character_boundaries(self):
        text="Hey Brillio hiring freshers now today indeed"
        chars=list(text)
        starts=[i*0.07 for i in range(len(chars))]
        ends=[(i+1)*0.07 for i in range(len(chars))]
        words=word_alignment({"characters":chars,
            "character_start_times_seconds":starts,
            "character_end_times_seconds":ends},text)
        self.assertEqual(words[0]["text"],"Hey")
        self.assertEqual(words[0]["start"],0)
        self.assertAlmostEqual(words[1]["start"],0.28,places=2)
        self.assertEqual(len(words),7)

    def test_rejects_mismatched_words(self):
        with self.assertRaises(ValueError):
            word_alignment({"characters":["a"],"character_start_times_seconds":[0],
                            "character_end_times_seconds":[.3]},"b")

    def test_ass_highlights_current_word_at_its_actual_timestamp(self):
        words=[{"text":str(i),"start":round(i*.25,3),
                "end":round((i+1)*.25,3)} for i in range(10)]
        with tempfile.TemporaryDirectory() as temp:
            dst=Path(temp)/"captions.ass"
            stat=create_ass(words,dst)
            text=dst.read_text()
            events=[l for l in text.splitlines() if l.startswith("Dialogue:")]
            self.assertEqual(stat["captionCount"],10)
            self.assertEqual(len(events),10)
            self.assertIn("0:00:00.00,0:00:00.25",events[0])
            self.assertIn("0:00:00.25,0:00:00.50",events[1])
            self.assertIn(r"\1c&H00AA4FFF&",events[0])
            self.assertIn("0:00:02.25,0:00:02.85",events[-1])

    def test_ass_escapes_script_markup(self):
        words=[{"text":x,"start":i*.2,"end":(i+1)*.2}
               for i,x in enumerate(["Brillio","{injection}","is","hiring","for","an","entry","role"])]
        with tempfile.TemporaryDirectory() as tmp:
            dst=Path(tmp)/"x.ass"
            create_ass(words,dst)
            self.assertNotIn("{injection}",dst.read_text())
            self.assertIn("injection",dst.read_text())


if __name__=="__main__":
    unittest.main()
