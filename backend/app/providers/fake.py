"""Deterministic providers for tests, local dev with no credentials, and store-reviewer demos."""

from __future__ import annotations

import asyncio
import re
import time
from collections.abc import AsyncIterator

from app.providers.base import (
    ACTION_FLAGS,
    AudioFormat,
    ProviderUnavailable,
    RedFlag,
    ScoreResult,
    ScoringContext,
    ShowAnswers,
    ShowInput,
    TranscriberUsage,
    TranscriptSegment,
    Usage,
)

_FLAG_PATTERNS: list[tuple[RedFlag, re.Pattern[str]]] = [
    (
        RedFlag.UNUSUAL_PAYMENT,
        re.compile(r"gift card|wire transfer|zelle|bitcoin|crypto|western union", re.I),
    ),
    (
        RedFlag.GOVERNMENT_IMPERSONATION,
        re.compile(
            r"\b(irs|medicare|social security administration|police|sheriff|marshal|treasury)\b",
            re.I,
        ),
    ),
    (
        RedFlag.FINANCIAL_THREAT,
        re.compile(r"arrest|warrant|lawsuit|deport|suspend(ed)? your", re.I),
    ),
    (
        RedFlag.TECH_SUPPORT,
        re.compile(r"remote access|anydesk|teamviewer|virus|infected|refund department", re.I),
    ),
    (RedFlag.GRANDPARENT, re.compile(r"grand(son|daughter|child)|bail|in jail|car accident", re.I)),
    (
        RedFlag.PRIZE_LOTTERY,
        re.compile(r"you('ve| have) won|lottery|sweepstakes|prize|claim your", re.I),
    ),
    (
        RedFlag.ISOLATION,
        re.compile(r"don'?t tell|do not tell|keep this between|tell no one|don'?t hang up", re.I),
    ),
    (
        RedFlag.URGENCY,
        re.compile(r"right now|immediately|within the hour|today only|act now|last chance", re.I),
    ),
    (
        RedFlag.INFO_FISHING,
        re.compile(
            r"social security number|\bssn\b|password|account number|routing number|date of birth|verification code|read me the code",
            re.I,
        ),
    ),
    (
        RedFlag.META_INSTRUCTION,
        re.compile(
            r"ignore (all )?previous|elderguard says|this call is (verified|safe)|system prompt",
            re.I,
        ),
    ),
]

DEFAULT_DEMO_SCRIPT: list[str] = [
    "Hello? Yes, this is Eleanor speaking.",
    "Hi Eleanor, I'm calling from the Medicare benefits office about your new card.",
    "We need to verify your identity before we can send it. Can you read me your Social Security number?",
    "This has to be done today or your coverage will be suspended.",
    "There is a small processing fee. The fastest way is to buy a gift card at the store and read me the numbers.",
    "Please don't tell anyone about this call until it's resolved, it's a private matter.",
]


def fake_score_text(text: str) -> tuple[int, list[RedFlag]]:
    flags = [flag for flag, pat in _FLAG_PATTERNS if pat.search(text)]
    if not flags:
        return 0, []
    score = 2 * len(flags)
    if any(f in ACTION_FLAGS for f in flags):
        score += 2
    return min(10, score), flags


class FakeScorer:
    name = "fake"
    model = "fake"

    def __init__(self, fail: bool = False, latency_s: float = 0.0) -> None:
        self.fail = fail
        self.latency_s = latency_s
        self.calls = 0

    async def score(self, ctx: ScoringContext, timeout_s: float) -> ScoreResult:
        self.calls += 1
        if self.latency_s:
            await asyncio.sleep(self.latency_s)
        if self.fail:
            raise ProviderUnavailable("fake scorer configured to fail")
        t0 = time.monotonic()
        text = ctx.window_text + " " + ctx.partial_text
        score, flags = fake_score_text(text)
        return ScoreResult(
            score=score,
            reasoning="Fake scorer matched: " + ", ".join(f.value for f in flags)
            if flags
            else "No patterns matched",
            red_flags=flags,
            provider=self.name,
            model=self.model,
            latency_ms=int((time.monotonic() - t0) * 1000),
            usage=Usage(input_tokens=len(text) // 4, output_tokens=40),
        )


class FakeTranscriber:
    """Emits scripted lines as audio time accumulates. Also accepts text directly for tests."""

    name = "fake"
    model = "fake"

    def __init__(
        self,
        script: list[str] | None = None,
        seconds_per_line: float = 5.0,
        fail: bool = False,
    ) -> None:
        self.script = list(script if script is not None else DEFAULT_DEMO_SCRIPT)
        self.seconds_per_line = seconds_per_line
        self.fail = fail
        self._queue: asyncio.Queue[TranscriptSegment | None] = asyncio.Queue()
        self._fmt = AudioFormat()
        self._audio_bytes = 0
        self._next_line = 0
        self._closed = False

    @property
    def audio_seconds(self) -> float:
        bytes_per_sec = self._fmt.sample_rate * (1 if self._fmt.encoding == "mulaw" else 2)
        return self._audio_bytes / bytes_per_sec

    async def start(self, fmt: AudioFormat) -> None:
        if self.fail:
            raise ProviderUnavailable("fake transcriber configured to fail")
        self._fmt = fmt

    async def push(self, audio: bytes) -> None:
        self._audio_bytes += len(audio)
        while (
            self._next_line < len(self.script)
            and self.audio_seconds >= (self._next_line + 1) * self.seconds_per_line
        ):
            i = self._next_line
            self._next_line += 1
            start_ms = int(i * self.seconds_per_line * 1000)
            end_ms = int((i + 1) * self.seconds_per_line * 1000)
            await self._queue.put(
                TranscriptSegment(
                    text=self.script[i], is_final=True, t_start_ms=start_ms, t_end_ms=end_ms
                )
            )

    async def feed_text(
        self, text: str, t_start_ms: int, t_end_ms: int, is_final: bool = True
    ) -> None:
        await self._queue.put(
            TranscriptSegment(
                text=text, is_final=is_final, t_start_ms=t_start_ms, t_end_ms=t_end_ms
            )
        )

    async def segments(self) -> AsyncIterator[TranscriptSegment]:
        while True:
            seg = await self._queue.get()
            if seg is None:
                return
            yield seg

    async def close(self) -> TranscriberUsage:
        if not self._closed:
            self._closed = True
            await self._queue.put(None)
        return TranscriberUsage(audio_seconds=self.audio_seconds)


class FakeSynthesizer:
    name = "fake"
    model = "fake"

    async def synthesize(self, text: str, voice_ref: str, fmt: str = "ulaw_8000") -> bytes:
        seconds = max(0.5, len(text) / 15.0)
        return bytes([0xFF]) * int(seconds * 8000)


class FakeMessageAnalyzer:
    name = "fake"
    model = "fake"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    async def analyze(self, inp: ShowInput, answers: ShowAnswers, timeout_s: float) -> ScoreResult:
        if self.fail:
            raise ProviderUnavailable("fake analyzer configured to fail")
        text = " ".join([inp.text, answers.who_is_it_from, answers.what_do_they_want])
        score, flags = fake_score_text(text)
        if inp.image_b64 and not flags:
            # The fake cannot read pictures. Like the real rubric, unreadable means middling.
            score = 4
        return ScoreResult(
            score=score,
            reasoning="Fake analyzer",
            red_flags=flags,
            provider=self.name,
            model=self.model,
        )
