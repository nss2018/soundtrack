"""命令行契约：退出码 0 = 成功，2 = 用法/数据错。"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from soundtrack.cli import main  # noqa: E402

GOOD = {
    "name": "unit-test",
    "bpm": 120,
    "sample_rate": 8000,
    "duration": 2.0,
    "master": 0.8,
    "tracks": [
        {"id": "a", "instrument": "pluck", "notes": [{"t": 0.0, "pitch": "C4", "dur": 0.4}]},
        {"id": "d", "instrument": "kick", "notes": [{"t": 0.2, "dur": 0.1}]},
    ],
}


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cues = os.path.join(self.tmp, "cue.json")
        with open(self.cues, "w") as f:
            json.dump(GOOD, f)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_info(self):
        self.assertEqual(main(["info", self.cues]), 0)

    def test_check(self):
        self.assertEqual(main(["check", self.cues]), 0)

    def test_list_instruments(self):
        self.assertEqual(main(["list"]), 0)

    def test_render_writes_wav(self):
        out = os.path.join(self.tmp, "out.wav")
        self.assertEqual(main(["render", self.cues, "-o", out]), 0)
        self.assertTrue(os.path.exists(out))
        self.assertGreater(os.path.getsize(out), 44)

    def test_render_defaults_to_sibling_wav(self):
        self.assertEqual(main(["render", self.cues]), 0)
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "cue.wav")))

    def test_render_quiet(self):
        self.assertEqual(
            main(["render", self.cues, "-o", os.path.join(self.tmp, "q.wav"), "-q"]), 0)

    def test_missing_file_is_exit_2(self):
        self.assertEqual(main(["check", os.path.join(self.tmp, "nope.json")]), 2)

    def test_bad_json_is_exit_2(self):
        bad = os.path.join(self.tmp, "bad.json")
        with open(bad, "w") as f:
            f.write("{ nope")
        self.assertEqual(main(["check", bad]), 2)

    def test_bad_score_shape_is_exit_2(self):
        bad = os.path.join(self.tmp, "empty.json")
        with open(bad, "w") as f:
            json.dump({"bpm": 120, "tracks": []}, f)
        self.assertEqual(main(["info", bad]), 2)

    def test_no_subcommand_is_exit_2(self):
        self.assertEqual(main([]), 2)


if __name__ == "__main__":
    unittest.main()
