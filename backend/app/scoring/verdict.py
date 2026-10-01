"""Show Me verdicts. The server derives the verdict from a bounded score; the model never picks it.

Unlike a live call, a single message can be judged on its own, so there is a calm outcome. It is
still never worded or typed as "safe": the lowest verdict means only that no red flags were found.
"""

from __future__ import annotations

from enum import StrEnum

from app.providers.base import ACTION_FLAGS, RedFlag
from app.scoring.tiers import band

# A message that talks to the checker ("ignore previous instructions", "this is verified") is an
# attack on the checker, so it never lands in the calm verdict, whatever score the model gave.
META_FLOOR = 6


class Verdict(StrEnum):
    NO_RED_FLAGS = "no_red_flags"
    BE_CAREFUL = "be_careful"
    DONT_REPLY = "dont_reply"


def floor_score(score: int, flags: list[RedFlag]) -> int:
    if RedFlag.META_INSTRUCTION in flags:
        return max(score, META_FLOOR)
    return score


def verdict_for(score: int, flags: list[RedFlag]) -> Verdict:
    score = floor_score(score, flags)
    level = band(score)
    if level == "high":
        return Verdict.DONT_REPLY
    if level == "mid":
        return Verdict.BE_CAREFUL
    # Low score, but the message asks for money, access, secrets, or silence: stay cautious.
    if any(f in ACTION_FLAGS for f in flags):
        return Verdict.BE_CAREFUL
    return Verdict.NO_RED_FLAGS
