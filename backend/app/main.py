"""Application factory. Run with: uvicorn app.main:create_app --factory"""

from __future__ import annotations

import sys
import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app import IMPORT_T0
from app.api import accounts, admin, deps, devices, guardians, health, internal, sessions
from app.logging_setup import configure_logging
from app.notify.push import FcmPushSender, LogPushSender, NotifyService
from app.persistence.config_service import ConfigService, StaticConfigSource
from app.providers.loader import load_flags, load_provider_config
from app.providers.metrics import LogUsageSink
from app.providers.registry import build_registry
from app.security.oidc import DevSchedulerVerifier, SchedulerVerifier
from app.sessions.accounts import AccountService, InMemoryAccountRepo
from app.sessions.store import InMemorySessionStore
from app.settings import Settings
from app.twilio import media, voice

log = structlog.get_logger("app")


class _Stages:
    """Milliseconds per startup stage, logged once as `startup_timing`. Timings only, no PII.

    `app_imports` is app.main and everything it imports. Interpreter and uvicorn start come before
    that; on Cloud Run they are the gap from the "Starting new instance" line to this event, minus
    total_ms. Later create_app() calls in the same process (tests) report app_imports as 0.
    """

    _imports_reported = False

    def __init__(self) -> None:
        self._t = time.perf_counter()
        self.ms: dict[str, int] = {"app_imports": 0}
        if not _Stages._imports_reported:
            _Stages._imports_reported = True
            self.ms["app_imports"] = round((self._t - IMPORT_T0) * 1000)

    def mark(self, stage: str) -> None:
        now = time.perf_counter()
        self.ms[stage] = round((now - self._t) * 1000)
        self._t = now


def create_app(settings: Settings | None = None) -> FastAPI:
    stages = _Stages()
    settings = settings or Settings()
    configure_logging(settings.log_level, json_output=settings.is_prod)
    _init_sentry(settings)
    stages.mark("settings")

    base_config = load_provider_config(settings.providers_config_path)
    base_flags = load_flags(settings.flags_config_path)

    if settings.use_firestore:
        from app.persistence.firestore import (
            FirestoreAccountRepo,
            FirestoreConfigSource,
            FirestoreSessionStore,
            FirestoreUsageSink,
            make_client,
        )

        client = make_client(settings.gcp_project)
        session_store = FirestoreSessionStore(client)
        account_repo = FirestoreAccountRepo(client)
        usage_sink = FirestoreUsageSink(client)
        config_source = FirestoreConfigSource(client)
    else:
        session_store = InMemorySessionStore()
        account_repo = InMemoryAccountRepo(settings)
        usage_sink = LogUsageSink()
        config_source = StaticConfigSource()
    stages.mark("store")

    config_service = ConfigService(
        base_config, base_flags, config_source, cache_seconds=settings.config_cache_seconds
    )
    registry = build_registry(settings, lambda: config_service.config)
    stages.mark("registry")
    push_sender = FcmPushSender(settings.gcp_project) if settings.use_fcm else LogPushSender()
    stages.mark("push")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            await _startup_checks()
        except Exception as e:
            # One short line first: the container exits right after, and Cloud Run can drop the
            # tail of a long traceback. Error text names settings, never secret values.
            log.error("startup_failed", error_type=type(e).__name__, error=str(e)[:500])
            sys.stdout.flush()
            sys.stderr.flush()
            raise
        yield

    async def _startup_checks() -> None:
        problems = settings.startup_problems()
        if problems:
            if settings.is_prod:
                raise RuntimeError(f"refusing to start in prod: {problems}")
            log.warning("startup_problems", problems=problems)
        if settings.twilio_auth_token is None:
            log.warning("twilio_auth_token_missing", detail="Twilio webhooks will return 503")
        await config_service.refresh(force=True)
        stages.mark("config_refresh")
        log.info("startup_timing", total_ms=sum(stages.ms.values()), **stages.ms)
        log.info(
            "startup",
            env=settings.env,
            store=settings.store,
            auth_mode=settings.auth_mode,
            notify=settings.notify,
            fake_providers=settings.fakes_enabled,
            scorers=[r.provider for r in registry.available_routes("scorer")],
            transcribers=[r.provider for r in registry.available_routes("transcriber")],
        )

    app = FastAPI(
        title="ElderGuard API",
        version="0.2.0",
        lifespan=lifespan,
        docs_url=None if settings.is_prod else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_prod else "/openapi.json",
    )
    app.state.settings = settings
    app.state.config_service = config_service
    app.state.config_source = config_source
    app.state.registry = registry
    app.state.session_store = session_store
    app.state.accounts = account_repo
    app.state.account_service = AccountService(account_repo, settings)
    app.state.usage_sink = usage_sink
    app.state.push_sender = push_sender
    app.state.notify = NotifyService(push_sender, account_repo)
    app.state.live_calls = {}
    app.state.limiter = deps.limiter
    if settings.use_firebase_auth:
        from app.security.firebase_auth import FirebaseIdentityAdmin, TokenVerifier

        app.state.token_verifier = TokenVerifier(settings.gcp_project)
        app.state.identity = FirebaseIdentityAdmin(settings.gcp_project)
    else:
        from app.security.firebase_auth import NoopIdentityAdmin

        app.state.identity = NoopIdentityAdmin()
    if settings.scheduler_service_account:
        app.state.scheduler_verifier = SchedulerVerifier(
            settings.scheduler_service_account, settings.public_base_url
        )
    elif not settings.is_prod:
        app.state.scheduler_verifier = DevSchedulerVerifier()
    stages.mark("auth")

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

    for r in (
        health.router,
        voice.router,
        media.router,
        accounts.router,
        guardians.router,
        devices.router,
        sessions.router,
        internal.router,
        admin.router,
    ):
        app.include_router(r)
    stages.mark("routes")
    return app


def _init_sentry(settings: Settings) -> None:
    if settings.sentry_dsn is None:
        return
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.sentry_dsn.get_secret_value(),
        environment=settings.env,
        send_default_pii=False,
        traces_sample_rate=0.0,
        before_send=_scrub_event,
    )


_SENSITIVE = {"transcript", "window_text", "partial_text", "text", "from_number", "phone", "From"}


def _scrub_event(event, hint):  # noqa: ANN001
    extra = event.get("extra") or {}
    for k in list(extra):
        if k in _SENSITIVE:
            extra[k] = "[redacted]"
    return event


async def _rate_limited(request, exc):  # noqa: ANN001
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=429, content={"detail": "rate limited"})
