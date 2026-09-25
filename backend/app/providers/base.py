"""Provider protocols and the bounded types every provider must return."""

from __future__ import annotations

from collections.abc import AsyncIterator
from enum import StrEnum
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field, field_validator


class RedFlag(StrEnum):
    GOVERNMENT_IMPERSONATION = "GOVERNMENT_IMPERSONATION"
    FINANCIAL_THREAT = "FINANCIAL_THREAT"
    UNUSUAL_PAYMENT = "UNUSUAL_PAYMENT"
    TECH_SUPPORT = "TECH_SUPPORT"
    GRANDPARENT = "GRANDPARENT"
    PRIZE_LOTTERY = "PRIZE_LOTTERY"
    ISOLATION = "ISOLATION"
    URGENCY = "URGENCY"
    INFO_FISHING = "INFO_FISHING"
    META_INSTRUCTION = "META_INSTRUCTION"


# Flags that describe the caller asking for something concrete: money, access, secrets, silence.
ACTION_FLAGS: frozenset[RedFlag] = frozenset(
    {RedFlag.UNUSUAL_PAYMENT, RedFlag.TECH_SUPPORT, RedFlag.INFO_FISHING, RedFlag.ISOLATION}
)

MAX_REASONING_CHARS = 240


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    audio_seconds: float = 0.0
    characters: int = 0


class ScoreResult(BaseModel):
    score: int = Field(ge=0, le=10)
    reasoning: str = ""
    red_flags: list[RedFlag] = Field(default_factory=list)
    provider: str
    model: str
    latency_ms: int = 0
    usage: Usage = Field(default_factory=Usage)

    @field_validator("score", mode="before")
    @classmethod
    def _clamp(cls, v):
        if isinstance(v, bool):
            raise ValueError("score must be numeric")
        n = int(round(float(v)))
        return max(0, min(10, n))

    @field_validator("reasoning", mode="before")
    @classmethod
    def _cap_reasoning(cls, v):
        text = " ".join(str(v or "").split())
        return text[:MAX_REASONING_CHARS]

    @field_validator("red_flags", mode="before")
    @classmethod
    def _dedupe_flags(cls, v):
        seen: list[RedFlag] = []
        for item in v or []:
            try:
                flag = RedFlag(str(item).strip().upper())
            except ValueError:
                continue
            if flag not in seen:
                seen.append(flag)
        return seen


class ScoringContext(BaseModel):
    window_text: str
    partial_text: str = ""
    prior_flags: list[RedFlag] = Field(default_factory=list)
    elapsed_s: float = 0.0
    watch_list: list[str] = Field(default_factory=list)


class TranscriptSegment(BaseModel):
    text: str
    is_final: bool
    t_start_ms: int
    t_end_ms: int


class AudioFormat(BaseModel):
    encoding: Literal["mulaw", "pcm16"] = "mulaw"
    sample_rate: int = 8000
    channels: int = 1


class TranscriberUsage(BaseModel):
    audio_seconds: float = 0.0


class ShowInput(BaseModel):
    kind: Literal["text", "image", "audio_transcript"]
    text: str = ""
    image_media_type: str | None = None
    image_b64: str | None = None


class ShowAnswers(BaseModel):
    who_is_it_from: str = ""
    what_do_they_want: str = ""


class ProviderError(Exception):
    """Base for provider failures. Callers treat these as 'unknown', never as 'safe'."""


class ProviderNotConfigured(ProviderError):
    pass


class ProviderUnavailable(ProviderError):
    pass


class ProviderRefused(ProviderUnavailable):
    pass


class ProviderBadOutput(ProviderError):
    pass


@runtime_checkable
class ScamScorer(Protocol):
    name: str
    model: str

    async def score(self, ctx: ScoringContext, timeout_s: float) -> ScoreResult: ...


@runtime_checkable
class StreamingTranscriber(Protocol):
    name: str
    model: str

    async def start(self, fmt: AudioFormat) -> None: ...

    async def push(self, audio: bytes) -> None: ...

    def segments(self) -> AsyncIterator[TranscriptSegment]: ...

    async def close(self) -> TranscriberUsage: ...


@runtime_checkable
class VoiceSynthesizer(Protocol):
    name: str
    model: str

    async def synthesize(self, text: str, voice_ref: str, fmt: str = "ulaw_8000") -> bytes: ...


@runtime_checkable
class MessageAnalyzer(Protocol):
    name: str
    model: str

    async def analyze(
        self, inp: ShowInput, answers: ShowAnswers, timeout_s: float
    ) -> ScoreResult: ...
