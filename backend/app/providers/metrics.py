"""Per-call usage events with an estimated cost. This is the raw material for grant reporting."""

from __future__ import annotations

import time
from typing import Protocol

import structlog
from pydantic import BaseModel, Field

from app.providers.base import Usage

log = structlog.get_logger("usage")

# USD per unit. Tokens are per million; audio is per minute; characters are per thousand.
PRICE_TABLE: dict[str, dict[str, dict[str, float]]] = {
    "anthropic": {
        "claude-sonnet-5": {"input": 2.0, "output": 10.0, "cache_read": 0.20, "cache_write": 2.50},
        "claude-opus-5-5": {"input": 4.0, "output": 20.0, "cache_read": 0.20, "cache_write": 5.00},
        "claude-opus-5": {"input": 5.0, "output": 25.0, "cache_read": 0.50, "cache_write": 6.25},
        "claude-haiku-4-5": {"input": 1.0, "output": 5.0, "cache_read": 0.10, "cache_write": 1.25},
    },
    "gemini": {
        "gemini-flash-latest": {
            "input": 0.30,
            "output": 2.50,
            "cache_read": 0.03,
            "cache_write": 0.30,
        },
    },
    "deepgram": {"nova-3": {"audio_minute": 0.0077}},
    "assemblyai": {"universal-streaming": {"audio_minute": 0.0025}},
    "google_stt": {"chirp_3": {"audio_minute": 0.016}},
    "elevenlabs": {"eleven_flash_v2_5": {"per_1k_chars": 0.05}},
    "fake": {"fake": {}},
}


def estimate_cost(provider: str, model: str, usage: Usage) -> float:
    prices = PRICE_TABLE.get(provider, {}).get(model, {})
    cost = 0.0
    cost += usage.input_tokens / 1e6 * prices.get("input", 0.0)
    cost += usage.output_tokens / 1e6 * prices.get("output", 0.0)
    cost += usage.cache_read_tokens / 1e6 * prices.get("cache_read", 0.0)
    cost += usage.cache_write_tokens / 1e6 * prices.get("cache_write", 0.0)
    cost += usage.audio_seconds / 60.0 * prices.get("audio_minute", 0.0)
    cost += usage.characters / 1000.0 * prices.get("per_1k_chars", 0.0)
    return round(cost, 6)


class UsageEvent(BaseModel):
    ts: float = Field(default_factory=time.time)
    session_id: str | None = None
    account_id: str | None = None
    capability: str
    provider: str
    model: str
    usage: Usage = Field(default_factory=Usage)
    latency_ms: int = 0
    est_cost_usd: float = 0.0
    ok: bool = True


class UsageSink(Protocol):
    async def emit(self, event: UsageEvent) -> None: ...


class LogUsageSink:
    """Writes one structured log line per event. Firestore sink arrives in M1."""

    def __init__(self) -> None:
        self.events: list[UsageEvent] = []

    async def emit(self, event: UsageEvent) -> None:
        if event.est_cost_usd == 0.0:
            event.est_cost_usd = estimate_cost(event.provider, event.model, event.usage)
        self.events.append(event)
        log.info(
            "usage",
            session_id=event.session_id,
            capability=event.capability,
            provider=event.provider,
            model=event.model,
            latency_ms=event.latency_ms,
            est_cost_usd=event.est_cost_usd,
            ok=event.ok,
            **event.usage.model_dump(),
        )
