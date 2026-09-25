"""Application factory. Run with: uvicorn app.main:create_app --factory"""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api import dev_sessions, health
from app.logging_setup import configure_logging
from app.providers.loader import load_flags, load_provider_config
from app.providers.metrics import LogUsageSink
from app.providers.registry import build_registry
from app.sessions.accounts import DevAllowlistResolver
from app.sessions.store import InMemorySessionStore
from app.settings import Settings
from app.twilio import media, voice

log = structlog.get_logger("app")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings.log_level, json_output=settings.is_prod)

    provider_config = load_provider_config(settings.providers_config_path)
    flags = load_flags(settings.flags_config_path)
    registry = build_registry(settings, provider_config)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        insecure = settings.insecure_defaults_in_use()
        if insecure:
            if settings.is_prod:
                raise RuntimeError(f"refusing to start in prod with default secrets: {insecure}")
            log.warning("insecure_default_secrets", keys=insecure)
        if settings.twilio_auth_token is None:
            log.warning("twilio_auth_token_missing", detail="Twilio webhooks will return 503")
        log.info(
            "startup",
            env=settings.env,
            fake_providers=settings.fakes_enabled,
            scorers=[r.provider for r in registry.available_routes("scorer")],
            transcribers=[r.provider for r in registry.available_routes("transcriber")],
        )
        yield

    app = FastAPI(
        title="ElderGuard API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if settings.is_prod else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_prod else "/openapi.json",
    )
    app.state.settings = settings
    app.state.provider_config = provider_config
    app.state.flags = flags
    app.state.registry = registry
    app.state.session_store = InMemorySessionStore()
    app.state.accounts = DevAllowlistResolver(settings)
    app.state.usage_sink = LogUsageSink()
    app.state.live_calls = {}
    app.state.limiter = dev_sessions.limiter

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type"],
        )
    app.add_middleware(SlowAPIMiddleware)
    app.add_exception_handler(RateLimitExceeded, _rate_limited)

    app.include_router(health.router)
    app.include_router(voice.router)
    app.include_router(media.router)
    app.include_router(dev_sessions.router)
    return app


async def _rate_limited(request, exc):  # noqa: ANN001
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=429, content={"detail": "rate limited"})
