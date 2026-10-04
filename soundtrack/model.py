"""Score model —— 把 cues.json 变成可校验、可推算时长的数据结构。

手机环境（a-Shell / Pythonista / iOS 上的第三方 Python）可能停在 3.7、3.8，
所以这里刻意只使用 typing 模块的类型注解，不碰 PEP 604 的 `X | Y`、
也不依赖 dataclasses 的高版本特性。
"""

from __future__ import annotations

import json
import re

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

__all__ = [
    "Note",
    "Track",
    "Score",
    "ScoreError",
    "note_to_midi",
    "midi_to_freq",
    "load",
]

_SEMITONE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

_NOTE_RE = re.compile(r"^([A-Ga-g])([#b]?)(-?\d)$")

# 合成器把每个音的尾巴拖多长（秒）。用来推算总时长，保证最后一个音不会被截掉。
_TAIL = {"kick": 0.14, "snare": 0.05, "hat": 0.02, "blip": 0.06}


class ScoreError(ValueError):
    """cues.json 写错了。

    抛的时候一定带上位置（哪个 track、第几个音），
    不把裸 KeyError 丢给使用者去猜。
    """


def note_to_midi(name):
    """'A4' -> 69，'C#3' -> 49，'Eb5' -> 75。"""
    m = _NOTE_RE.match(name.strip())
    if not m:
        raise ScoreError("音名没认出来: %r。写成 'A4'、'C#3'、'Eb5' 这种形式" % name)
    letter, accidental, octave = m.group(1), m.group(2), int(m.group(3))
    semi = _SEMITONE[letter.upper()]
    if accidental == "#":
        semi += 1
    elif accidental == "b":
        semi -= 1
    return (octave + 1) * 12 + semi


def midi_to_freq(midi):
    """69 -> 440.0 Hz。"""
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


def _pick(src, names, where, kind):
    """从 dict 里按别名列表取值，找不到就报一条人能读懂的话。"""
    for n in names:
        if n in src:
            v = src[n]
            if v is not None:
                return v
    raise ScoreError("%s: 缺 %s（可选 %s）" % (where, kind, " / ".join(names)))


@dataclass
class Note:
    """时间轴上的一个音。"""

    t: float = 0.0          # 起始秒
    pitch: Optional[str] = None   # 'A4'；None 表示休止（只占时间不出声）
    dur: float = 0.5        # 时长（秒）
    gain: float = 1.0       # 在所属轨道内的音量

    @classmethod
    def from_dict(cls, raw, bpm, where):
        if isinstance(raw, str) and raw.strip() == "-":
            # 简写：'-' 表示休止一小节，手写 JSON 时省事
            spb = 60.0 / bpm
            return cls(t=0.0, pitch=None, dur=spb, gain=1.0)
        if not isinstance(raw, dict):
            raise ScoreError("%s: 一个音应该是对象，收到 %s" % (where, type(raw).__name__))

        beat = raw.get("beat")
        beats = raw.get("beats")
        spb = 60.0 / bpm
        if beat is not None:
            t = float(beat) * spb
        else:
            t = float(_pick(raw, ("t", "time", "at", "start"), where, "起始时间"))

        if beats is not None:
            dur = float(beats) * spb
        else:
            dur = float(_pick(raw, ("dur", "length", "dur_s"), where, "时长"))

        pitch = raw.get("pitch", raw.get("note", raw.get("n")))
        gain = raw.get("gain", raw.get("gain_s", raw.get("vel", raw.get("velocity"))))
        if gain is None:
            gain = 1.0

        if pitch is not None and pitch != "-":
            pitch = str(pitch)
            if not _NOTE_RE.match(pitch.strip()):
                raise ScoreError("%s: 音名 %r 不对，应该是 'A4' 这种" % (where, pitch))

        return cls(t=t, pitch=pitch, dur=dur, gain=float(gain))


@dataclass
class Track:
    """一条乐器轨。"""

    id: str = "track0"
    instrument: str = "pluck"
    notes: List[Note] = field(default_factory=list)
    gain: float = 1.0
    loop: Optional[float] = None   # 循环长度（秒）；游戏 BGM 的刚需

    @classmethod
    def from_dict(cls, raw, bpm, where):
        if not isinstance(raw, dict):
            raise ScoreError("%s: 一条轨道应该是对象" % where)
        tid = _pick(raw, ("id", "name"), where, "轨道名")
        inst = _pick(raw, ("instrument", "inst", "voice"), where, "乐器名")
        notes_raw = raw.get("notes")
        if notes_raw is None:
            raise ScoreError("%s: 缺 notes 列表" % where)
        if not isinstance(notes_raw, list):
            raise ScoreError("%s: notes 应该是列表" % where)

        notes = []
        for i, n in enumerate(notes_raw):
            notes.append(Note.from_dict(n, bpm, "%s.notes[%d]" % (where, i)))

        loop = raw.get("loop")
        return cls(
            id=str(tid),
            instrument=str(inst).lower(),
            notes=notes,
            gain=float(raw.get("gain", 1.0)),
            loop=None if loop is None else float(loop),
        )


@dataclass
class Score:
    """一整首曲子。"""

    name: str = "untitled"
    bpm: float = 120.0
    duration: Optional[float] = None   # 秒；留空就按最后一个音推算
    sample_rate: int = 22050
    master: float = 0.9
    tracks: List[Track] = field(default_factory=list)

    # ---- 构造 ---------------------------------------------------------

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            raise ScoreError("顶层应该是对象，收到 %s" % type(d).__name__)

        bpm = float(d.get("bpm", 120))
        if bpm <= 0:
            raise ScoreError("bpm 得是正数，现在是 %r" % d.get("bpm"))

        tracks_raw = d.get("tracks", [])
        if not isinstance(tracks_raw, list):
            raise ScoreError("tracks 应该是列表")
        if not tracks_raw:
            raise ScoreError("tracks 是空的 —— 至少放一条轨道")

        tracks = []
        seen = set()
        for i, t in enumerate(tracks_raw):
            tr = Track.from_dict(t, bpm, "tracks[%d]" % i)
            if tr.id in seen:
                raise ScoreError("轨道 id 重复了: %r" % tr.id)
            seen.add(tr.id)
            tracks.append(tr)

        sr = int(d.get("sample_rate", 22050))
        if sr < 4000:
            raise ScoreError("sample_rate 太低（%d），声音会糊成一坨" % sr)

        dur = d.get("duration")
        return cls(
            name=str(d.get("name", "untitled")),
            bpm=bpm,
            duration=None if dur is None else float(dur),
            sample_rate=sr,
            master=float(d.get("master", 0.9)),
            tracks=tracks,
        )

    # ---- 推算 ---------------------------------------------------------

    def implied_duration(self, tail_hint=None):
        """不写 duration 时用这个：最后一个音的尾 + 一点余量。"""
        end = 0.0
        for tr in self.tracks:
            span = tr.loop or 0.0
            if span:
                # 循环轨：音符会按 loop 周期反复铺，所以至少认一个完整周期，
                # 否则 loop=8 的 BGM 在没写 duration 时会只出一个 0.4 秒的碎片。
                last = max(n.t for n in tr.notes)
                end = max(end, span + last + 0.5)
                continue
            for n in tr.notes:
                tail = tail_hint(tr.instrument) if callable(tail_hint) else 0.5
                end = max(end, n.t + n.dur + tail)
        if self.duration is not None:
            return max(end, float(self.duration))
        return end if end > 0 else 1.0

    def resolved_duration(self):
        return self.implied_duration(_TAIL)

    def summary(self):
        """给 CLI 的 info 子命令用，纯文本，手机上也好看。"""
        lines = [
            "《%s》  %g BPM  %d Hz  %d 轨"
            % (self.name, self.bpm, self.sample_rate, len(self.tracks)),
            "时长 %s（推算）" % _fmt(self.resolved_duration()),
        ]
        for tr in self.tracks:
            extra = ""
            if tr.loop:
                extra = "  循环 %s" % _fmt(tr.loop)
            lines.append(
                "  · %-10s %-8s %d 音%s"
                % (tr.id, tr.instrument, len(tr.notes), extra)
            )
        total_notes = sum(len(t.notes) for t in self.tracks)
        lines.append("共 %d 个音" % total_notes)
        return "\n".join(lines)


def _fmt(sec):
    if sec < 60:
        return "%.2fs" % sec
    m, s = divmod(sec, 60)
    return "%d:%02d" % (int(m), int(s + 1e-9))


def load(path):
    """读 cues.json 得到 Score。文件不存在 / JSON 坏了都给一条人话。"""
    try:
        with open(path, "r") as f:
            raw = f.read()
    except IOError as e:
        raise ScoreError("读不了 %s: %s" % (path, e.strerror or str(e)))
    try:
        d = json.loads(raw)
    except ValueError as e:
        raise ScoreError("%s 不是合法 JSON: %s" % (path, e))

    if isinstance(d, dict) and "cues" in d and "tracks" not in d:
        raise ScoreError(
            "%s 是时间轴文件（有 cues 键，没有 tracks），不是配乐文件。\n"
            "  用这个把它变成配乐:  python -m soundtrack adapt %s" % (path, path)
        )

    sc = Score.from_dict(d)
    sc.name = d.get("name", sc.name)
    return sc
