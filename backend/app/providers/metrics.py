"""Per-call usage events with an estimated cost. This is the raw material for grant reporting."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any, Protocol

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

    async def events_between(self, start: float, end: float) -> list[UsageEvent]: ...

    async def write_rollup(self, month: str, rollup: dict[str, Any]) -> None: ...

    async def read_rollup(self, month: str) -> dict[str, Any] | None: ...


def month_bounds(month: str) -> tuple[float, float]:
    """'YYYY-MM' -> (start_ts, end_ts) in UTC."""
    year, mon = (int(x) for x in month.split("-"))
    start = datetime(year, mon, 1, tzinfo=UTC)
    end = datetime(year + (mon == 12), 1 if mon == 12 else mon + 1, 1, tzinfo=UTC)
    return start.timestamp(), end.timestamp()


def month_of(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=UTC).strftime("%Y-%m")


def previous_month(month: str) -> str:
    year, mon = (int(x) for x in month.split("-"))
    return f"{year - 1}-12" if mon == 1 else f"{year}-{mon - 1:02d}"


def rollup_events(month: str, events: list[UsageEvent], computed_at: float) -> dict[str, Any]:
    """The grant report: cost and volume by provider and capability for one month."""
    by_provider: dict[str, dict[str, float]] = {}
    by_capability: dict[str, dict[str, float]] = {}
    sessions: set[str] = set()
    accounts: set[str] = set()
    total = 0.0
    audio_seconds = 0.0
    failures = 0
    for e in events:
        total += e.est_cost_usd
        audio_seconds += e.usage.audio_seconds
        failures += 0 if e.ok else 1
        if e.session_id:
            sessions.add(e.session_id)
        if e.account_id:
            accounts.add(e.account_id)
        prov = by_provider.setdefault(e.provider, {"calls": 0, "est_cost_usd": 0.0})
        prov["calls"] += 1
        prov["est_cost_usd"] += e.est_cost_usd
        cap = by_capability.setdefault(e.capability, {"calls": 0, "est_cost_usd": 0.0})
        cap["calls"] += 1
        cap["est_cost_usd"] += e.est_cost_usd
    for d in (*by_provider.values(), *by_capability.values()):
        d["est_cost_usd"] = round(d["est_cost_usd"], 4)
    return {
        "month": month,
        "total_cost_usd": round(total, 4),
        "by_provider": by_provider,
        "by_capability": by_capability,
        "events": len(events),
        "failures": failures,
        "sessions": len(sessions),
        "active_accounts": len(accounts),
        "minutes": round(audio_seconds / 60.0, 1),
        "computed_at": computed_at,
    }


class LogUsageSink:
    """Keeps events in memory and logs each one. Dev and tests only."""

    def __init__(self) -> None:
        self.events: list[UsageEvent] = []
        self.rollups: dict[str, dict[str, Any]] = {}

    async def events_between(self, start: float, end: float) -> list[UsageEvent]:
        return [e for e in self.events if start <= e.ts < end]

    async def write_rollup(self, month: str, rollup: dict[str, Any]) -> None:
        self.rollups[month] = rollup

    async def read_rollup(self, month: str) -> dict[str, Any] | None:
        return self.rollups.get(month)

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
