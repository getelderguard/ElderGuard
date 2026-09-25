"""G.711 mu-law <-> 16-bit PCM and a 2x upsampler. Pure Python; Python 3.13 dropped audioop."""

from __future__ import annotations

from array import array

_BIAS = 0x84
_CLIP = 32635


def _decode_one(u: int) -> int:
    u = ~u & 0xFF
    sign = u & 0x80
    exponent = (u >> 4) & 0x07
    mantissa = u & 0x0F
    sample = ((mantissa << 3) + _BIAS) << exponent
    sample -= _BIAS
    return -sample if sign else sample


_DECODE_TABLE = [_decode_one(i) for i in range(256)]


def mulaw_to_pcm16(data: bytes) -> bytes:
    out = array("h", (_DECODE_TABLE[b] for b in data))
    return out.tobytes()


def _encode_one(sample: int) -> int:
    sign = 0
    if sample < 0:
        sign = 0x80
        sample = -sample
    if sample > _CLIP:
        sample = _CLIP
    sample += _BIAS
    exponent = 7
    mask = 0x4000
    while exponent > 0 and not (sample & mask):
        exponent -= 1
        mask >>= 1
    mantissa = (sample >> (exponent + 3)) & 0x0F
    return ~(sign | (exponent << 4) | mantissa) & 0xFF


def pcm16_to_mulaw(data: bytes) -> bytes:
    samples = array("h")
    samples.frombytes(data)
    return bytes(_encode_one(s) for s in samples)


def upsample_2x(pcm16: bytes) -> bytes:
    """Linear interpolation from 8 kHz to 16 kHz."""
    samples = array("h")
    samples.frombytes(pcm16)
    if not samples:
        return b""
    out = array("h")
    for i, s in enumerate(samples):
        out.append(s)
        nxt = samples[i + 1] if i + 1 < len(samples) else s
        out.append((s + nxt) // 2)
    return out.tobytes()


SILENCE_MULAW = 0xFF


def silence(seconds: float, sample_rate: int = 8000) -> bytes:
    return bytes([SILENCE_MULAW]) * int(seconds * sample_rate)
