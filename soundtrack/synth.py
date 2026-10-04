"""合成器 —— 加法合成（振荡器 + 泛音 + ADSR + 一阶低通）。

刻意不用 numpy / scipy：手机上装不了包，而这东西本来也不需要。
全靠 math.sin 和 array，Python 3.7 就能跑。
"""

from __future__ import annotations

import math
import random
from array import array

from .model import ScoreError, midi_to_freq, note_to_midi

__all__ = ["INSTRUMENTS", "DRUMS", "render_score", "instruments"]

TAU = 6.283185307179586

_SEED = 20261004

# 波形：sine / triangle / saw / square
INSTRUMENTS = {
    "pad":    dict(wave="sine",     a=0.30, d=0.20, s=0.65, r=0.60, lpf=2000, harm=2, vib=0.0,   vibrato_hz=5.0),
    "organ":  dict(wave="sine",     a=0.04, d=0.06, s=0.85, r=0.12, lpf=2800, harm=3, vib=0.0,   vibrato_hz=5.0),
    "pluck":  dict(wave="triangle", a=0.004, d=0.22, s=0.06, r=0.14, lpf=4200, harm=1, vib=0.0,   vibrato_hz=5.0),
    "bass":   dict(wave="square",   a=0.006, d=0.14, s=0.55, r=0.10, lpf=380,  harm=1, vib=0.0,   vibrato_hz=5.0),
    "lead":   dict(wave="saw",      a=0.010, d=0.12, s=0.60, r=0.18, lpf=4800, harm=2, vib=0.004, vibrato_hz=5.5),
    "blip":   dict(wave="sine",     a=0.002, d=0.08, s=0.02, r=0.03, lpf=8000, harm=1, vib=0.0,   vibrato_hz=5.0),
    "bell":   dict(wave="sine",     a=0.002, d=1.10, s=0.0,  r=0.45, lpf=6000, harm=4, vib=0.0,   vibrato_hz=5.0),
    "click":  dict(wave="square",   a=0.001, d=0.02, s=0.0,  r=0.01, lpf=3500, harm=1, vib=0.0,   vibrato_hz=5.0),
}

DRUMS = ("kick", "snare", "hat", "clap")


def instruments():
    """所有可用的乐器名。"""
    return sorted(list(INSTRUMENTS.keys()) + list(DRUMS))


def _wave(kind, phase):
    if kind == "triangle":
        return 4.0 * abs((phase - math.floor(phase)) - 0.5) - 1.0
    if kind == "saw":
        return 2.0 * (phase - math.floor(phase)) - 1.0
    if kind == "square":
        return 1.0 if (phase - math.floor(phase)) < 0.5 else -1.0
    return math.sin(TAU * phase)


def _hit(buf, i0, count, fn):
    """从 i0 起往 buf 里铺 count 个采样；越界的裁掉，不报错。"""
    if i0 >= len(buf) or count <= 0:
        return
    if i0 < 0:
        count += i0
        i0 = 0
        if count <= 0:
            return
    if count > len(buf) - i0:
        count = len(buf) - i0
    for i in range(count):
        buf[i0 + i] += fn(i)


# ---- 旋律 / 音色轨 -------------------------------------------------------

def _render_note(buf, sr, t0, note, spec, amp):
    """一个音 = 振荡器 + 泛音 + ADSR + 低通，写进 buf。"""
    pitch = note.pitch
    if pitch is None:
        return

    a = float(spec["a"]); d = float(spec["d"])
    s = float(spec["s"]); r = float(spec["r"])
    lpf = float(spec.get("lpf", 8000))
    harm = int(spec.get("harm", 1))
    vib = float(spec.get("vib", 0.0))
    vib_hz = float(spec.get("vibrato_hz", 5.0))
    wave = spec["wave"]
    dur_s = note.dur

    freq = midi_to_freq(note_to_midi(pitch))
    count = int(round((dur_s + min(r, 0.9)) * sr))
    i0 = int(round(t0 * sr))

    alpha = 1.0 - math.exp(-TAU * lpf / sr)
    if alpha > 1.0:
        alpha = 1.0
    norm = (1.0 + sum(0.6 / h for h in range(2, harm + 1))) if harm > 1 else 1.0

    lp = [0.0]   # 低通状态
    ph = [0.0]   # 相位累积；vibrato 会临时改步长

    def fn(i):
        t = i / sr
        step = freq / sr
        if vib:
            step *= (1.0 + vib * math.sin(TAU * vib_hz * t))
        phase = ph[0] + step
        ph[0] = phase

        x = _wave(wave, phase)
        if harm > 1:
            for h in range(2, harm + 1):
                x += _wave(wave, phase * h) * (0.6 / h)
            x /= norm

        if t < a:
            env = (t / a) if a > 0 else 1.0
        elif t < a + d:
            k = ((t - a) / d) if d > 0 else 1.0
            env = 1.0 + (s - 1.0) * k
        elif t <= dur_s:
            env = s
        else:
            rt = t - dur_s
            env = s * ((1.0 - rt / r) if r > 0 else 0.0)
            if env < 0.0:
                env = 0.0

        y = x * env
        if alpha < 1.0:
            lp[0] += alpha * (y - lp[0])
            y = lp[0]
        return y * amp

    _hit(buf, i0, count, fn)


# ---- 鼓 -----------------------------------------------------------------

def _kick(buf, sr, t0, amp):
    ph = [0.0]
    def fn(i):
        t = i / sr
        ph[0] += (46.0 + 92.0 * math.exp(-t * 26.0)) / sr
        return math.sin(TAU * ph[0]) * math.exp(-t * 8.5) * amp
    _hit(buf, int(round(t0 * sr)), int(sr * 0.34), fn)


def _snare(buf, sr, t0, amp):
    st = {"lp": 0.0}
    def fn(i):
        t = i / sr
        tone = math.sin(TAU * 186.0 * t) * math.exp(-t * 34.0)
        n = random.uniform(-1.0, 1.0) * math.exp(-t * 24.0)
        x = tone + n * 0.8
        st["lp"] += 0.45 * (x - st["lp"])
        return st["lp"] * amp
    _hit(buf, int(round(t0 * sr)), int(sr * 0.22), fn)


def _hat(buf, sr, t0, amp):
    prev = [0.0]
    def fn(i):
        t = i / sr
        n = random.uniform(-1.0, 1.0)
        y = n - prev[0]        # 差分近似高通，只留高频碎噪音
        prev[0] = n
        return y * math.exp(-t * 62.0) * amp
    _hit(buf, int(round(t0 * sr)), int(sr * 0.09), fn)


def _render_drum(buf, sr, t0, amp, which):
    if which == "kick":
        _kick(buf, sr, t0, amp)
    elif which == "snare":
        _snare(buf, sr, t0, amp)
    elif which == "hat":
        _hat(buf, sr, t0, amp)
    elif which == "clap":
        _hat(buf, sr, t0, amp * 0.6)
        _hat(buf, sr, t0 + 0.012, amp * 0.45)
        _hat(buf, sr, t0 + 0.022, amp * 0.3)


# ---- 轨道 / 整曲 ---------------------------------------------------------

def render_track(buf, sr, tr, total):
    amp = tr.gain

    if tr.loop and tr.loop > 0:
        span = tr.loop
        reps = int(total / span) + 1
        events = []
        for k in range(reps):
            shift = k * span
            for n in tr.notes:
                events.append((n.t + shift, n))
    else:
        events = [(n.t, n) for n in tr.notes]

    if tr.instrument in DRUMS:
        for t, _ in events:
            _render_drum(buf, sr, t, amp, tr.instrument)
        return

    spec = INSTRUMENTS.get(tr.instrument)
    if spec is None:
        raise ScoreError(
            "乐器 %r 不存在（轨道 %r）。可选: %s"
            % (tr.instrument, tr.id, ", ".join(instruments()))
        )
    for t, n in events:
        _render_note(buf, sr, t, n, spec, amp)


def render_score(score):
    """把 Score 混成一条单声道波形（array('d')，取值 -1..1）。"""
    total = score.resolved_duration()
    sr = score.sample_rate
    n = int(math.ceil(total * sr)) + 1
    buf = array("d", bytes(8 * n))

    random.seed(_SEED)          # 噪声也固定种子，保证同样输入同样输出
    for tr in score.tracks:
        if tr.gain <= 0.0:
            continue
        render_track(buf, sr, tr, total)

    _normalize(buf, score.master)
    return buf


def _normalize(buf, master):
    peak = 0.0
    for v in buf:
        av = v if v >= 0.0 else -v
        if av > peak:
            peak = av
    if peak <= 0.0:
        return
    k = master / peak
    if k > 1.0:
        k = 1.0
    for i in range(len(buf)):
        v = buf[i] * k
        buf[i] = 1.0 if v > 1.0 else (-1.0 if v < -1.0 else v)
