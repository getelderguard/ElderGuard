"""Free regex pre-screen. A hit forces an immediate score regardless of cadence."""

from __future__ import annotations

import re

TRIPWIRE_PATTERNS: dict[str, re.Pattern[str]] = {
    "gift_card": re.compile(r"gift ?cards?|itunes card|google play card|apple card", re.I),
    "government": re.compile(
        r"\b(irs|medicare|social security|sheriff|warrant|treasury|federal agent)\b", re.I
    ),
    "payment_rail": re.compile(
        r"wire transfer|zelle|venmo|cash ?app|bitcoin|crypto|western union|moneygram", re.I
    ),
    "secrecy": re.compile(
        r"don'?t tell|do not tell|keep this (between|private|quiet)|don'?t hang up", re.I
    ),
    "codes": re.compile(
        r"verification code|one[- ]time code|read (me )?the (code|numbers)|security code", re.I
    ),
    "family_emergency": re.compile(r"grand(son|daughter|child)|\bbail\b|in jail|accident", re.I),
    "remote_access": re.compile(
        r"remote access|anydesk|teamviewer|screen share|install (this|the) app", re.I
    ),
    "meta": re.compile(r"elderguard|ignore (all )?previous|this call is (verified|safe)", re.I),
}


def tripwire_hits(text: str) -> list[str]:
    return [name for name, pat in TRIPWIRE_PATTERNS.items() if pat.search(text)]
