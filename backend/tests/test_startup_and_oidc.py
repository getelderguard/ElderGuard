"""Startup timing event and the cached OIDC cert transport."""

from __future__ import annotations

import asyncio

import cachecontrol
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import app.main as main
from app.main import create_app
from app.security import oidc
from tests.conftest import make_settings


def test_startup_timing_logged_once_with_stages(monkeypatch):
    logs = []

    class Recorder:
        def info(self, event, **kw):
            logs.append({"event": event, **kw})

        warning = error = info

    # create_app() reconfigures structlog, so structlog.testing.capture_logs would be overridden.
    monkeypatch.setattr(main, "log", Recorder())
    with TestClient(create_app(make_settings())):
        pass
    timing = [e for e in logs if e["event"] == "startup_timing"]
    assert len(timing) == 1
    stages = {
        "app_imports",
        "settings",
        "store",
        "registry",
        "push",
        "auth",
        "routes",
        "config_refresh",
    }
    assert stages <= timing[0].keys()
    assert timing[0]["total_ms"] == sum(timing[0][k] for k in stages)


def test_scheduler_verify_reuses_one_cached_transport(monkeypatch):
    monkeypatch.setattr(oidc, "_cert_request", None)
    seen = []

    def fake_verify(token, request, audience):
        seen.append(request)
        raise ValueError("bad token")

    monkeypatch.setattr("google.oauth2.id_token.verify_oauth2_token", fake_verify)
    verifier = oidc.SchedulerVerifier("sched@example.test", "https://api.example.test")
    for _ in range(2):
        with pytest.raises(HTTPException):
            asyncio.run(verifier.verify("t", "/internal/sweep"))
    assert len(seen) == 2 and seen[0] is seen[1]
    adapter = seen[0].session.get_adapter("https://www.googleapis.com/oauth2/v1/certs")
    assert isinstance(adapter, cachecontrol.CacheControlAdapter)


def test_real_provider_sdks_load_after_startup_not_during():
    # Fresh interpreter: other tests may already have imported the SDKs into this one.
    code = """
import sys
from pydantic import SecretStr
from tests.conftest import make_settings
from app.providers.loader import load_provider_config
from app.providers.registry import build_registry, preload_providers
s = make_settings(fake_providers="0", anthropic_api_key=SecretStr("x"), stt_api_key=SecretStr("x"))
build_registry(s, load_provider_config(s.providers_config_path))
assert "anthropic" not in sys.modules and "websockets" not in sys.modules, "imported at startup"
preload_providers()
assert "anthropic" in sys.modules and "websockets" in sys.modules
"""
    import subprocess
    import sys

    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
