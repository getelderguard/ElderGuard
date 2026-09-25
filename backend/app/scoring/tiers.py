"""Live tiers. There is deliberately no 'safe' or 'clear' tier."""

from __future__ import annotations

from enum import StrEnum


class Tier(StrEnum):
    LISTENING = "listening"
    CAUTION = "caution"
    STOP = "stop"
    UNKNOWN = "unknown"
    NO_AUDIO = "no_audio"


def band(score: int) -> str:
    if score <= 3:
        return "low"
    if score <= 6:
        return "mid"
    return "high"
