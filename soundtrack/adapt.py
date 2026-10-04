"""把别处的时间轴（比如 code-to-film 渲染出的 __cues）变成一首配乐。

渲染脚本每到一个小节/事件点就吐一个 cue，这里按 cue 的 label 挑乐器，
于是画面和声音天然对齐 —— 不用手工再敲一遍音符。

    {"t": 2.4, "label": "chapter"}      秒
    {"beat": 8, "kind": "success"}      拍
    {"t": 1.0, "label": "tap"}          未知 label 兜底 pluck，不炸
"""

from __future__ import annotations

import re
from typing import Dict, List

from .model import Note, Score, ScoreError, Track

__all__ = ["from_cues", "GLOSSARY"]

# (正则, 乐器, 音名, 时长秒, 增益)。顺序有意义，先命中先算。
GLOSSARY = [
    (r"(error|fail|wrong|deny|invalid)",                     "blip",   "A2", 0.20, 0.55),
    (r"(back|cancel|close|dismiss|reject)",                  "blip",   "F3", 0.16, 0.60),
    (r"(success|correct|right|pass|win|coin|reward|unlock)", "bell",   "E5", 0.50, 0.70),
    (r"(start|go|begin|confirm|ok|done)",                    "blip",   "C5", 0.14, 0.60),
    (r"(chapter|section|title|scene|transition|ending)",     "pad",    "A3", 2.40, 0.50),
    (r"(tap|click|select|choose|item|hover|press)",          "click",  "A5", 0.03, 0.50),
    (r"(swipe|drag|scroll|move)",                            "blip",   "D5", 0.10, 0.45),
    (r"(whoosh|swoosh|reveal|zoom|expand)",                  "pad",    "C4", 0.90, 0.40),
]


def _classify(label):
    s = str(label).lower()
    for pattern, inst, pitch, dur, gain in GLOSSARY:
        if re.search(pattern, s):
            return inst, pitch, dur, gain
    return "pluck", "D4", 0.25, 0.50


def _time_of(cue, bpm, index):
    """有 t/time/beat 就用它；纯标签（字符串 cue）按序号一拍一个排开。"""
    if "beat" in cue and cue["beat"] is not None:
        return float(cue["beat"]) * (60.0 / bpm)
    for key in ("t", "time", "at", "start", "timestamp", "position"):
        if cue.get(key) is not None:
            return float(cue[key])
    if index is not None:
        return index * (60.0 / bpm)
    raise ScoreError("cue 里找不到时间（要有 t / time / beat）: %r" % (cue,))


def from_cues(cues, sample_rate=22050, master=0.85, name="from-cues", bpm=96.0):
    """cues: list of dict / str  ->  Score（按乐器自动分轨）。"""
    if isinstance(cues, dict):
        cues = cues.get("cues") or cues.get("events") or []
    if not isinstance(cues, (list, tuple)):
        raise ScoreError("cues 应该是列表，收到 %s" % type(cues).__name__)

    buckets = {}   # 乐器名 -> [Note]
    for index, cue in enumerate(cues):
        is_string = isinstance(cue, str)
        if is_string:
            cue = {"label": cue}
        if not isinstance(cue, dict):
            raise ScoreError("每个 cue 应该是对象或字符串，收到 %r" % (cue,))
        label = cue.get("label", cue.get("kind", cue.get("type", "")))
        inst, pitch, dur, gain = _classify(label)
        buckets.setdefault(inst, []).append(
            Note(t=_time_of(cue, bpm, index if is_string else None),
                 pitch=pitch, dur=dur, gain=gain)
        )

    if not buckets:
        raise ScoreError("cues 是空的 —— 至少给一个")

    tracks = [
        Track(id=inst, instrument=inst, notes=notes)
        for inst, notes in sorted(buckets.items())
    ]
    return Score(name=name, bpm=bpm, sample_rate=sample_rate, master=master, tracks=tracks)
