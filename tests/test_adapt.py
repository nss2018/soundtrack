"""把别人的时间轴（code-to-film 的 __cues）翻译成配乐。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from soundtrack.model import ScoreError  # noqa: E402
from soundtrack.adapt import from_cues  # noqa: E402


class TestClassify(unittest.TestCase):
    def test_tap_becomes_click(self):
        sc = from_cues([{"t": 0.0, "label": "tap"}])
        self.assertEqual(sc.tracks[0].instrument, "click")

    def test_wrong_becomes_low_blip(self):
        sc = from_cues([{"t": 0.0, "label": "wrong answer"}])
        self.assertEqual(sc.tracks[0].instrument, "blip")
        self.assertEqual(sc.tracks[0].notes[0].pitch, "A2")

    def test_success_becomes_bell(self):
        sc = from_cues([{"t": 0.0, "label": "success"}])
        self.assertEqual(sc.tracks[0].instrument, "bell")

    def test_chapter_becomes_pad(self):
        sc = from_cues([{"t": 0.0, "label": "chapter 2"}])
        self.assertEqual(sc.tracks[0].instrument, "pad")

    def test_unknown_label_falls_back(self):
        sc = from_cues([{"t": 0.0, "label": "teleport"}])
        self.assertEqual(sc.tracks[0].instrument, "pluck")

    def test_string_cue(self):
        sc = from_cues(["tap", "success"])
        self.assertTrue({t.instrument for t in sc.tracks} >= {"click", "bell"})


class TestTiming(unittest.TestCase):
    def test_beat_converted_by_bpm(self):
        sc = from_cues([{"beat": 2, "label": "tap"}], bpm=120)
        self.assertAlmostEqual(sc.tracks[0].notes[0].t, 1.0)

    def test_time_in_seconds(self):
        sc = from_cues([{"t": 3.5, "label": "tap"}], bpm=120)
        self.assertAlmostEqual(sc.tracks[0].notes[0].t, 3.5)

    def test_tracks_grouped_by_instrument(self):
        sc = from_cues([{"t": 0, "label": "tap"}, {"t": 1, "label": "success"}])
        self.assertEqual(len(sc.tracks), 2)


class TestErrors(unittest.TestCase):
    def test_empty_cues(self):
        with self.assertRaises(ScoreError):
            from_cues([])

    def test_cue_without_time(self):
        with self.assertRaises(ScoreError):
            from_cues([{"label": "tap"}])

    def test_not_a_list(self):
        with self.assertRaises(ScoreError):
            from_cues("tap")

    def test_dict_input_picks_cues_key(self):
        sc = from_cues({"cues": [{"t": 0.0, "label": "tap"}]})
        self.assertEqual(len(sc.tracks), 1)


if __name__ == "__main__":
    unittest.main()
