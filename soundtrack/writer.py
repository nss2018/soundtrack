"""WAV 写出。只用到 wave + array —— 这两个在 iOS 的任何 Python 里都有。"""

from __future__ import annotations

import sys
import wave
from array import array

__all__ = ["write_wav", "wav_size_note"]

_LIMIT_HI = 32767
_LIMIT_LO = -32768


def write_wav(path, samples, sample_rate):
    """samples 是 array('d')，取值 -1..1；写成一个 16-bit PCM 单声道 wav。"""
    out = array("h", bytes(2 * len(samples)))
    i = 0
    for v in samples:
        iv = int(round(v * 32767.0))
        if iv > _LIMIT_HI:
            iv = _LIMIT_HI
        elif iv < _LIMIT_LO:
            iv = _LIMIT_LO
        out[i] = iv
        i += 1
    if sys.byteorder == "big":
        out.byteswap()

    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(sample_rate))
        w.writeframes(out.tobytes())
    return path


def wav_size_note(path, sample_rate):
    """给人看的体积说明，顺带确认文件真的写进去了。"""
    import os
    n = os.path.getsize(path)
    secs = n / float(sample_rate * 2)
    if n > 1024 * 1024:
        return "%.1f MB / %.1f 秒" % (n / 1048576.0, secs)
    return "%.0f KB / %.1f 秒" % (n / 1024.0, secs)
