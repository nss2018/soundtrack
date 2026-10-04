"""Soundtrack as code —— 用几行 JSON 谱写配乐，零第三方依赖。

    import soundtrack as st

    score = st.load("cues.json")
    st.render(score, "out.wav")

只有标准库：model / synth / writer / adapt 四个模块，加一起不到 700 行。
iOS 上的 a-Shell、Pythonista、普通 CPython 3.7+ 都能跑。
"""

from __future__ import annotations

from .adapt import from_cues
from .model import (
    Note,
    Score,
    ScoreError,
    Track,
    load,
    midi_to_freq,
    note_to_midi,
)
from .synth import DRUMS, INSTRUMENTS, instruments, render_score
from .writer import write_wav

__version__ = "1.0.0"

__all__ = [
    "Score",
    "Track",
    "Note",
    "ScoreError",
    "load",
    "render",
    "render_samples",
    "instruments",
    "INSTRUMENTS",
    "DRUMS",
    "from_cues",
    "note_to_midi",
    "midi_to_freq",
    "write_wav",
]


def render_samples(score):
    """Score -> array('d')，取值 -1..1。不落盘，想自己处理 PCM 就用这个。"""
    return render_score(score)


def render(score, out):
    """Score -> wav 文件。返回输出路径。"""
    buf = render_score(score)
    write_wav(out, buf, score.sample_rate)
    return out
