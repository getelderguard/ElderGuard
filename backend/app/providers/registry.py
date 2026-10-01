"""Capability -> provider factories. Config picks the route; the registry builds the instance."""

from __future__ import annotations

import importlib
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.providers.base import ProviderNotConfigured
from app.providers.config import CAPABILITIES, ProviderConfig, Route
from app.settings import Settings

Factory = Callable[[Settings, Route], Any]
Configured = Callable[[Settings], bool]


@dataclass
class _Entry:
    factory: Factory
    is_configured: Configured


ConfigGetter = Callable[[], ProviderConfig]


@dataclass
class ProviderRegistry:
    settings: Settings
    config_getter: ConfigGetter
    _entries: dict[str, dict[str, _Entry]] = field(default_factory=dict)

    @property
    def config(self) -> ProviderConfig:
        return self.config_getter()

    def register(
        self,
        capability: str,
        provider: str,
        factory: Factory,
        is_configured: Configured = lambda _s: True,
    ) -> None:
        self._entries.setdefault(capability, {})[provider] = _Entry(factory, is_configured)

    def is_configured(self, capability: str, provider: str) -> bool:
        entry = self._entries.get(capability, {}).get(provider)
        return bool(entry and entry.is_configured(self.settings))

    def available_routes(self, capability: str) -> list[Route]:
        return [
            r
            for r in self.config.routing(capability).routes
            if self.is_configured(capability, r.provider)
        ]

    def choose(self, capability: str, rng: random.Random | None = None) -> Route:
        routes = self.available_routes(capability)
        if not routes:
            raise ProviderNotConfigured(f"no configured provider for {capability}")
        return self.config.choose(capability, routes, rng)

    def chain(
        self, capability: str, first: Route | None = None, rng: random.Random | None = None
    ) -> list[Route]:
        """Primary route followed by configured fallbacks in the order the config lists them."""
        primary = first or self.choose(capability, rng)
        routing = self.config.routing(capability)
        by_provider = {r.provider: r for r in routing.routes}
        chain = [primary]
        for name in routing.fallback_order:
            r = by_provider.get(name)
            if r and r.provider != primary.provider and self.is_configured(capability, r.provider):
                chain.append(r)
        return chain

    def build(self, capability: str, route: Route) -> Any:
        entry = self._entries.get(capability, {}).get(route.provider)
        if entry is None or not entry.is_configured(self.settings):
            raise ProviderNotConfigured(f"{route.provider} is not configured for {capability}")
        return entry.factory(self.settings, route)


# Transcriber first: it is needed as soon as audio arrives, the scorer a few seconds later.
PROVIDER_MODULES = (
    "app.providers.deepgram_transcriber",
    "app.providers.anthropic_scorer",
    "app.providers.anthropic_analyzer",
)


def preload_providers() -> int:
    """Import the real provider SDKs so the first live call does not pay for it. Returns ms."""
    t0 = time.perf_counter()
    for name in PROVIDER_MODULES:
        importlib.import_module(name)
    return round((time.perf_counter() - t0) * 1000)


def build_registry(settings: Settings, config: ProviderConfig | ConfigGetter) -> ProviderRegistry:
    getter: ConfigGetter = config if callable(config) else (lambda c=config: c)  # type: ignore[assignment]
    registry = ProviderRegistry(settings=settings, config_getter=getter)
    config = getter()
    if settings.fakes_enabled:
        _register_fakes(registry, config, fail=settings.fakes_fail)
        return registry

    # The SDK modules are imported on first build, not here: on Cloud Run they take seconds to
    # import, and the server should pass its startup probe first. main.py preloads them in a
    # background thread right after startup; a build that races it waits on the import lock.
    def anthropic_scorer(s: Settings, r: Route) -> Any:
        from app.providers.anthropic_scorer import AnthropicScorer

        return AnthropicScorer(
            api_key=s.anthropic_api_key.get_secret_value(),
            model=r.model or "claude-sonnet-5",
            effort=str(r.params.get("effort", "low")),
            max_tokens=int(r.params.get("max_tokens", 400)),
        )

    def anthropic_analyzer(s: Settings, r: Route) -> Any:
        from app.providers.anthropic_analyzer import AnthropicMessageAnalyzer

        return AnthropicMessageAnalyzer(
            api_key=s.anthropic_api_key.get_secret_value(),
            model=r.model or "claude-sonnet-5",
            effort=str(r.params.get("effort", "low")),
            max_tokens=int(r.params.get("max_tokens", 400)),
        )

    def deepgram_transcriber(s: Settings, r: Route) -> Any:
        from app.providers.deepgram_transcriber import DeepgramTranscriber

        return DeepgramTranscriber(
            api_key=s.stt_api_key.get_secret_value(),
            model=r.model or "nova-3",
            params=r.params,
        )

    registry.register(
        "scorer",
        "anthropic",
        anthropic_scorer,
        is_configured=lambda s: s.anthropic_api_key is not None,
    )
    registry.register(
        "message_analyzer",
        "anthropic",
        anthropic_analyzer,
        is_configured=lambda s: s.anthropic_api_key is not None,
    )
    registry.register(
        "transcriber",
        "deepgram",
        deepgram_transcriber,
        is_configured=lambda s: s.stt_api_key is not None,
    )
    return registry


def _register_fakes(registry: ProviderRegistry, config: ProviderConfig, fail: bool) -> None:
    from app.providers.fake import FakeMessageAnalyzer, FakeScorer, FakeSynthesizer, FakeTranscriber

    factories: dict[str, Factory] = {
        "scorer": lambda s, r: FakeScorer(fail=fail),
        "transcriber": lambda s, r: FakeTranscriber(fail=fail, script=r.params.get("script")),
        "tts": lambda s, r: FakeSynthesizer(),
        "message_analyzer": lambda s, r: FakeMessageAnalyzer(fail=fail),
    }
    known = {"anthropic", "gemini", "deepgram", "google_stt", "assemblyai", "elevenlabs", "fake"}
    for capability in CAPABILITIES:
        names = {r.provider for r in config.routing(capability).routes} | known
        for name in names:
            registry.register(capability, name, factories[capability])
