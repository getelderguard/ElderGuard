"""Data shapes for the corpus generator."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Beat:
    """One exchange. The caller says one of `caller`; the senior answers from `senior`
    (or from the resistance-level pools when `senior` is empty)."""

    caller: list[str]
    senior: list[str] = field(default_factory=list)
    optional: bool = False
    action: bool = False  # the caller asks for money, access, codes, or silence


@dataclass(frozen=True)
class Scenario:
    category: str
    label: str  # "scam" | "benign"
    openers: list[str]
    beats: list[Beat]
    closers: list[str] = field(default_factory=list)
    senior_opener: list[str] = field(
        default_factory=lambda: ["Hello?", "Yes, hello.", "Hello, who is this?", "Speaking."]
    )
    # When True, the same variant index is used for the senior opener and every beat, so a
    # call about a forgotten tablet password stays about the tablet (variant lists line up).
    aligned: bool = False
    # Personal scams (grandchild, romance) get their own padding lines instead of the
    # institutional "let me pull up your file" material.
    personal: bool = False
