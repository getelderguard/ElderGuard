"""Live configuration: YAML defaults with a cached Firestore overlay on top.

Operators flip providers, limits, the kill switch, and feature flags with infra/scripts/*.py.
The backend re-reads the overlay every CONFIG_CACHE_SECONDS, so a change lands within that window.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Protocol

import structlog

from app.providers.config import Flags, ProviderConfig

log = structlog.get_logger("config")


class ConfigSource(Protocol):
    async def read(self, doc: str) -> dict[str, Any] | None: ...


class StaticConfigSource:
    """In-memory overlay for tests and local runs."""

    def __init__(self) -> None:
        self.docs: dict[str, dict[str, Any]] = {}

    async def read(self, doc: str) -> dict[str, Any] | None:
        return self.docs.get(doc)

    def set(self, doc: str, data: dict[str, Any] | None) -> None:
        if data is None:
            self.docs.pop(doc, None)
        else:
            self.docs[doc] = data


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class ConfigService:
    def __init__(
        self,
        base_config: ProviderConfig,
        base_flags: Flags,
        source: ConfigSource,
        cache_seconds: float = 30.0,
    ) -> None:
        self._base_config = base_config
        self._base_flags = base_flags
        self._source = source
        self._ttl = cache_seconds
        self._config = base_config
        self._flags = base_flags
        self._loaded_at = 0.0
        self._lock = asyncio.Lock()

    @property
    def config(self) -> ProviderConfig:
        """Last known config. Cheap; used on hot paths that cannot await."""
        return self._config

    @property
    def flags(self) -> Flags:
        return self._flags

    async def refresh(self, force: bool = False) -> None:
        if not force and time.monotonic() - self._loaded_at < self._ttl:
            return
        async with self._lock:
            if not force and time.monotonic() - self._loaded_at < self._ttl:
                return
            try:
                providers = await self._source.read("providers")
                flags = await self._source.read("flags")
            except Exception as e:  # noqa: BLE001 - keep serving the last good config
                log.warning("config_overlay_read_failed", error=type(e).__name__)
                self._loaded_at = time.monotonic()
                return
            try:
                cfg_data = deep_merge(self._base_config.model_dump(), _strip(providers))
                self._config = ProviderConfig.model_validate(cfg_data)
                flag_data = deep_merge(self._base_flags.model_dump(), _strip(flags))
                self._flags = Flags.model_validate(flag_data)
            except Exception as e:  # noqa: BLE001 - a bad overlay must not take the service down
                log.error("config_overlay_invalid", error=str(e)[:200])
            self._loaded_at = time.monotonic()

    async def get_config(self) -> ProviderConfig:
        await self.refresh()
        return self._config

    async def get_flags(self) -> Flags:
        await self.refresh()
        return self._flags


def _strip(doc: dict[str, Any] | None) -> dict[str, Any]:
    if not doc:
        return {}
    return {k: v for k, v in doc.items() if not k.startswith("_")}
