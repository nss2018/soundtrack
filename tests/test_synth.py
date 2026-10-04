"""合成器：出声、不爆、可复现、循环轨会展开。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from soundtrack.model import Note, Score, ScoreError, Track  # noqa: E402
from soundtrack.synth import render_score  # noqa: E402


def _score(inst="pluck", notes=None, **kw):
    return Score(name="t", bpm=120, sample_rate=8000, master=0.8, tracks=[
        Track(id="a", instrument=inst,
              notes=notes if notes is not None else [Note(t=0.0, pitch="A4", dur=0.5)])
    ], **kw)


class TestRender(unittest.TestCase):
    def test_produces_sound(self):
        buf = render_score(_score())
        self.assertGreater(len(buf), 1000)
        peak = max(abs(v) for v in buf)
        self.assertGreater(peak, 0.05, "全静音是 bug")

    def test_peak_capped_at_master(self):
        buf = render_score(_score())
        peak = max(abs(v) for v in buf)
        self.assertLessEqual(peak, 0.8 + 1e-9)

    def test_deterministic(self):
        a = render_score(_score())
        b = render_score(_score())
        self.assertEqual(len(a), len(b))
        for x, y in zip(a, b):
            self.assertEqual(x, y)

    def test_unknown_instrument_raises(self):
        with self.assertRaises(ScoreError):
            render_score(_score(inst="theremin"))

    def test_silence_instrument_yields_zero_buffer(self):
        buf = render_score(_score(inst="pluck", notes=[Note(t=0.0, pitch=None, dur=0.2)]))
        self.assertTrue(all(v == 0.0 for v in buf))

    def test_silence_does_not_crash(self):
        sc = Score(name="e", bpm=120, sample_rate=4000, master=0.5,
                   tracks=[Track(id="a", instrument="blip", notes=[])])
        buf = render_score(sc)
        self.assertEqual(len(buf) > 0, True)


class TestEnvelope(unittest.TestCase):
    def test_pluck_is_loud_then_fades(self):
        buf = render_score(_score(inst="pluck", notes=[Note(t=0.0, pitch="A4", dur=0.3)]))
        n = len(buf)
        head = max(abs(v) for v in buf[: n // 10])
        tail_idx = int(n * 0.95)
        tail = max(abs(buf[i]) for i in range(tail_idx, min(n, tail_idx + 80)))
        self.assertGreater(head, tail, "包络应该往下滑")

    def test_pad_slow_attack(self):
        buf = render_score(_score(inst="pad", notes=[Note(t=0.0, pitch="A3", dur=1.0)]))
        n = len(buf)
        start = max(abs(v) for v in buf[: n // 40])
        mid = max(abs(v) for v in buf[n // 4: n // 2])
        self.assertLess(start, mid, "pad 应该软起音")


class TestLoop(unittest.TestCase):
    def test_loop_repeats_notes(self):
        notes = [Note(t=0.0, pitch="C4", dur=0.4)]
        sc = _score(inst="pluck", notes=notes)
        sc.tracks[0].loop = 2.0
        buf = render_score(sc)
        total = len(buf) / 8000.0
        self.assertGreater(total, 2.0, "loop 轨应该铺满整段")

    def test_loop_keeps_repeat_silently(self):
        sc = _score(inst="pluck", notes=[Note(t=0.0, pitch="C4", dur=0.2)])
        sc.tracks[0].loop = 1.0
        buf = render_score(sc)
        self.assertGreater(max(abs(v) for v in buf), 0.0)


class TestDrums(unittest.TestCase):
    def test_kick_sounds(self):
        buf = render_score(_score(inst="kick", notes=[Note(t=0.0, dur=0.2)]))
        self.assertGreater(max(abs(v) for v in buf), 0.05)

    def test_snare_sounds(self):
        buf = render_score(_score(inst="snare", notes=[Note(t=0.0, dur=0.2)]))
        self.assertGreater(max(abs(v) for v in buf), 0.05)

    def test_hat_is_short(self):
        buf = render_score(_score(inst="hat", notes=[Note(t=0.0, dur=0.2)]))
        n = len(buf)
        tail_idx = int(n * 0.6)
        tail = max(abs(v) for v in buf[tail_idx:]) if n > tail_idx else 0.0
        self.assertLess(tail, 0.3, "hat 应该收得很快")


if __name__ == "__main__":
    unittest.main()
