"""cues.json 的解析与校验。"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from soundtrack.model import (  # noqa: E402
    Score, ScoreError, load, midi_to_freq, note_to_midi,
)


class TestPitch(unittest.TestCase):
    def test_note_to_midi(self):
        self.assertEqual(note_to_midi("A4"), 69)
        self.assertEqual(note_to_midi("C4"), 60)
        self.assertEqual(note_to_midi("A3"), 57)
        self.assertEqual(note_to_midi("C#3"), 49)
        self.assertEqual(note_to_midi("Eb5"), 75)
        self.assertEqual(note_to_midi("Bb1"), 34)   # B1=35, 降半音->34
        self.assertEqual(note_to_midi("B1"), 35)

    def test_bad_pitch(self):
        for bad in ["H4", "A", "4", "A#44", ""]:
            with self.assertRaises(ScoreError):
                note_to_midi(bad)

    def test_midi_to_freq(self):
        self.assertAlmostEqual(midi_to_freq(69), 440.0, places=6)
        self.assertAlmostEqual(midi_to_freq(81), 880.0, places=6)
        self.assertAlmostEqual(midi_to_freq(57), 220.0, places=6)

    def test_octave_roundtrip(self):
        for name in ["C2", "F#3", "Bb4", "E5"]:
            self.assertAlmostEqual(
                midi_to_freq(note_to_midi(name)),
                midi_to_freq(note_to_midi(name)),
            )


class TestNoteParsing(unittest.TestCase):
    def test_alias_t(self):
        n = Score.from_dict({"bpm": 120, "tracks": [
            {"id": "a", "instrument": "pluck", "notes": [{"time": 1.5, "dur": 0.5}]}
        ]}).tracks[0].notes[0]
        self.assertAlmostEqual(n.t, 1.5)
        self.assertAlmostEqual(n.dur, 0.5)

    def test_beat_converts_with_bpm(self):
        sc = Score.from_dict({"bpm": 120, "tracks": [
            {"id": "a", "instrument": "pluck", "notes": [{"beat": 2, "beats": 1}]}
        ]})
        n = sc.tracks[0].notes[0]
        self.assertAlmostEqual(n.t, 1.0)      # 120bpm → 一拍 0.5s
        self.assertAlmostEqual(n.dur, 0.5)

    def test_rest_shorthand(self):
        sc = Score.from_dict({"bpm": 120, "tracks": [
            {"id": "a", "instrument": "pluck", "notes": ["-"]}
        ]})
        n = sc.tracks[0].notes[0]
        self.assertIsNone(n.pitch)
        self.assertAlmostEqual(n.dur, 0.5)

    def test_missing_field_errors(self):
        with self.assertRaises(ScoreError):
            Score.from_dict({"bpm": 120, "tracks": [
                {"id": "a", "instrument": "pluck", "notes": [{"t": 0.0}]}
            ]})

    def test_bad_instrument_name_is_not_caught_here(self):
        # 乐器名合法性由 synth 判断，model 阶段放过
        sc = Score.from_dict({"bpm": 120, "tracks": [
            {"id": "a", "instrument": "theremin", "notes": [{"t": 0, "dur": 0.5}]}
        ]})
        self.assertEqual(sc.tracks[0].instrument, "theremin")


class TestScoreValidation(unittest.TestCase):
    def test_empty_tracks(self):
        with self.assertRaises(ScoreError):
            Score.from_dict({"bpm": 120, "tracks": []})

    def test_zero_bpm(self):
        with self.assertRaises(ScoreError):
            Score.from_dict({"bpm": 0, "tracks": [
                {"id": "a", "instrument": "pluck", "notes": [{"t": 0, "dur": 1}]}
            ]})

    def test_dup_track_id(self):
        with self.assertRaises(ScoreError):
            Score.from_dict({"bpm": 120, "tracks": [
                {"id": "same", "instrument": "pluck", "notes": []},
                {"id": "same", "instrument": "bass", "notes": []},
            ]})

    def test_low_sample_rate(self):
        with self.assertRaises(ScoreError):
            Score.from_dict({"bpm": 120, "sample_rate": 100, "tracks": [
                {"id": "a", "instrument": "pluck", "notes": []}
            ]})

    def test_duration_override_is_a_floor(self):
        sc = Score.from_dict({
            "bpm": 120, "duration": 99,
            "tracks": [{"id": "a", "instrument": "pluck",
                        "notes": [{"t": 0, "dur": 0.5}]}],
        })
        self.assertGreaterEqual(sc.resolved_duration(), 99)


class TestLoad(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_missing_file(self):
        with self.assertRaises(ScoreError):
            load(os.path.join(self.tmp, "nope.json"))

    def test_broken_json(self):
        p = os.path.join(self.tmp, "bad.json")
        with open(p, "w") as f:
            f.write("{ this is not json")
        with self.assertRaises(ScoreError):
            load(p)

    def test_good_file(self):
        p = os.path.join(self.tmp, "ok.json")
        with open(p, "w") as f:
            json.dump({"name": "x", "bpm": 90, "tracks": [
                {"id": "a", "instrument": "pluck", "notes": [{"t": 0, "dur": 0.5}]}
            ]}, f)
        sc = load(p)
        self.assertEqual(sc.name, "x")
        self.assertEqual(sc.bpm, 90)


if __name__ == "__main__":
    unittest.main()
