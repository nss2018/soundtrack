"""命令行入口。手机上没装 pip 的话，`python -m soundtrack` 也够用。

    python -m soundtrack render cues.json -o out.wav
    python -m soundtrack check cues.json
    python -m soundtrack info cues.json
    python -m soundtrack list
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import json

from .adapt import from_cues
from .model import ScoreError, load
from .synth import render_score, instruments
from .writer import wav_size_note, write_wav


def _say(msg):
    sys.stdout.write(msg + "\n")


def _dur(sec):
    if sec < 60:
        return "%.2fs" % sec
    return "%d:%02d" % (int(sec // 60), int(sec % 60))


def cmd_info(args):
    _say(load(args.cues).summary())
    return 0


def cmd_check(args):
    sc = load(args.cues)
    n = sum(len(t.notes) for t in sc.tracks)
    _say("ok  %s  %d 轨  %d 音  时长 %s"
         % (args.cues, len(sc.tracks), n, _dur(sc.resolved_duration())))
    return 0


def _write(args, sc):
    if args.sample_rate:
        sc.sample_rate = int(args.sample_rate)
    if args.master:
        sc.master = float(args.master)

    out = args.out
    if not out:
        out = os.path.splitext(args.cues)[0] + ".wav"

    t0 = time.time()
    buf = render_score(sc)
    write_wav(out, buf, sc.sample_rate)
    dt = time.time() - t0

    if not args.quiet:
        _say("%s  %g BPM  %d Hz  %d 轨"
             % (sc.name, sc.bpm, sc.sample_rate, len(sc.tracks)))
        _say("写入 %s  (%s)  用时 %.1fs"
             % (out, wav_size_note(out, sc.sample_rate), dt))
    return 0


def cmd_render(args):
    return _write(args, load(args.cues))


def cmd_adapt(args):
    """别人的时间轴（code-to-film 的 __cues）直接变成配乐。"""
    try:
        with open(args.cues, "r") as f:
            raw = json.load(f)
    except IOError as e:
        raise ScoreError("读不了 %s: %s" % (args.cues, e.strerror or str(e)))
    sc = from_cues(raw)
    return _write(args, sc)


def cmd_list(args):
    _say("可用乐器（%d）:" % len(instruments()))
    _say("  " + "  ".join(instruments()))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="python -m soundtrack",
        description="Soundtrack as code -- 用 JSON 谱写配乐，零第三方依赖",
    )
    sub = p.add_subparsers(dest="cmd")

    sp = sub.add_parser("render", help="渲染成 wav")
    sp.add_argument("cues")
    sp.add_argument("-o", "--out")
    sp.add_argument("--sample-rate", type=int)
    sp.add_argument("--master", type=float)
    sp.add_argument("-q", "--quiet", action="store_true")

    sp = sub.add_parser("check", help="只校验，不渲染")
    sp.add_argument("cues")

    sp = sub.add_parser("info", help="看时间轴摘要")
    sp.add_argument("cues")

    sp = sub.add_parser("adapt", help="时间轴 cues -> 配乐")
    sp.add_argument("cues")
    sp.add_argument("-o", "--out")
    sp.add_argument("--sample-rate", type=int)
    sp.add_argument("--master", type=float)
    sp.add_argument("-q", "--quiet", action="store_true")

    sp = sub.add_parser("list", help="列出可用乐器")
    sp.add_argument("cues", nargs="?")

    args = p.parse_args(argv)
    if not args.cmd:
        p.print_help()
        return 2

    handlers = {"render": cmd_render, "adapt": cmd_adapt, "check": cmd_check,
                "info": cmd_info, "list": cmd_list}

    try:
        return handlers[args.cmd](args)
    except ScoreError as e:
        sys.stderr.write("error: %s\n" % e)
        return 2
    except BrokenPipeError:
        return 2
