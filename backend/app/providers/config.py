"""Provider routing and limits. Seeded from YAML; Firestore overlays it in M1."""

from __future__ import annotations

import random
from typing import Any

from pydantic import BaseModel, Field

CAPABILITIES = ("scorer", "transcriber", "tts", "message_analyzer")


class Route(BaseModel):
    provider: str
    model: str = ""
    weight: int = Field(default=100, ge=0)
    params: dict[str, Any] = Field(default_factory=dict)


class CapabilityRouting(BaseModel):
    routes: list[Route] = Field(default_factory=list)
    fallback_order: list[str] = Field(default_factory=list)


class Limits(BaseModel):
    max_session_minutes: int = 45
    daily_minutes_per_account: int = 120
    line_initiated_daily_minutes: int = 15
    intent_ttl_seconds: int = 60
    no_audio_timeout_seconds: int = 20
    max_reconnect_attempts: int = 3
    velocity_calls: int = 3
    velocity_window_seconds: int = 600
    kill_switch: bool = False


class ProviderConfig(BaseModel):
    version: int = 1
    updated_by: str = "seed"
    capabilities: dict[str, CapabilityRouting] = Field(default_factory=dict)
    limits: Limits = Field(default_factory=Limits)

    def routing(self, capability: str) -> CapabilityRouting:
        return self.capabilities.get(capability, CapabilityRouting())

    def choose(
        self, capability: str, candidates: list[Route], rng: random.Random | None = None
    ) -> Route:
        """Weighted random among candidate routes; zero-weight routes are fallback-only."""
        weighted = [r for r in candidates if r.weight > 0]
        if not weighted:
            return candidates[0]
        rng = rng or random.Random()
        total = sum(r.weight for r in weighted)
        pick = rng.uniform(0, total)
        acc = 0.0
        for r in weighted:
            acc += r.weight
            if pick <= acc:
                return r
        return weighted[-1]


class Flags(BaseModel):
    announcement: bool = True
    takeover: bool = True
    guardian_alerts: bool = True
    show_me: bool = True
