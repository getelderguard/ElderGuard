"""Internal sweep and rollup, admin usage, config overlay, and prod startup guards."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.base import Usage
from app.providers.metrics import UsageEvent, month_of
from app.sessions.models import InitiatedBy, Session, SessionState
from tests.conftest import ENROLLED, SENIOR_HEADERS, STAFF_HEADERS, make_settings, twilio_post

SCHED = {"Authorization": "Bearer dev-scheduler"}


def test_internal_requires_scheduler_token(client):
    assert client.post("/internal/sweep").status_code == 401
    assert (
        client.post("/internal/sweep", headers={"Authorization": "Bearer nope"}).status_code == 401
    )
    assert client.post("/internal/sweep", headers=SCHED).status_code == 200


def test_sweep_expires_intents_and_abandons_stuck_sessions(client, app):
    store = app.state.session_store
    sid = client.post("/v1/sessions/intent", headers=SENIOR_HEADERS).json()["session_id"]
    import asyncio

    asyncio.run(store.update(sid, expires_at=time.time() - 1))
    stuck = asyncio.run(
        store.create(
            Session(
                account_id="dev-0142",
                phone_hash="h",
                state=SessionState.LIVE,
                initiated_by=InitiatedBy.APP,
                call_sid="CA-stuck",
                created_at=time.time() - 4 * 3600,
                live_at=time.time() - 4 * 3600,
            )
        )
    )
    r = client.post("/internal/sweep", headers=SCHED)
    assert r.json() == {"expired": 1, "abandoned": 1}
    assert client.get(f"/v1/sessions/{sid}", headers=SENIOR_HEADERS).json()["state"] == "expired"
    s = client.get(f"/v1/sessions/{stuck.id}", headers=SENIOR_HEADERS).json()
    assert s["state"] == "ended"


def test_rollup_and_admin_usage(client, app):
    import asyncio

    sink = app.state.usage_sink
    asyncio.run(
        sink.emit(
            UsageEvent(
                session_id="s1",
                account_id="a1",
                capability="scorer",
                provider="anthropic",
                model="claude-sonnet-5",
                usage=Usage(input_tokens=1000, output_tokens=100),
                latency_ms=900,
            )
        )
    )
    asyncio.run(
        sink.emit(
            UsageEvent(
                session_id="s1",
                account_id="a1",
                capability="transcriber",
                provider="deepgram",
                model="nova-3",
                usage=Usage(audio_seconds=120),
            )
        )
    )
    r = client.post("/internal/rollup", headers=SCHED)
    assert r.status_code == 200
    month = month_of(time.time())
    assert r.json()[month]["events"] == 2

    assert client.get("/admin/usage", headers=SENIOR_HEADERS).status_code == 403
    assert client.get("/admin/usage").status_code == 401
    r = client.get("/admin/usage", headers=STAFF_HEADERS)
    assert r.status_code == 200
    mtd = r.json()["month_to_date"]
    assert mtd["sessions"] == 1 and mtd["active_accounts"] == 1
    assert mtd["by_provider"]["anthropic"]["calls"] == 1
    assert mtd["minutes"] == 2.0
    assert mtd["total_cost_usd"] > 0
    assert r.json()["routing"]["scorer"][0]["provider"] == "anthropic"
    assert r.json()["flags"]["announcement"] is True


def test_kill_switch_overlay_rejects_calls_and_intents(client, app):
    import asyncio

    src = app.state.config_source
    src.set("providers", {"limits": {"kill_switch": True}, "version": 2})
    asyncio.run(app.state.config_service.refresh(force=True))
    assert client.get("/ready").json()["kill_switch"] is True
    r = twilio_post(
        client,
        "/twilio/voice/inbound",
        {"From": ENROLLED, "To": "+14155550100", "CallSid": "CA-k", "CallStatus": "ringing"},
    )
    assert "<Reject" in r.text
    assert client.post("/v1/sessions/intent", headers=SENIOR_HEADERS).status_code == 503

    src.set("providers", None)
    asyncio.run(app.state.config_service.refresh(force=True))
    assert client.get("/ready").json()["kill_switch"] is False


def test_provider_overlay_changes_routing_without_restart(client, app):
    import asyncio

    src = app.state.config_source
    src.set(
        "providers",
        {
            "version": 3,
            "capabilities": {
                "transcriber": {
                    "routes": [{"provider": "google_stt", "model": "chirp_3", "weight": 100}],
                    "fallback_order": [],
                }
            },
        },
    )
    asyncio.run(app.state.config_service.refresh(force=True))
    ready = client.get("/ready").json()
    assert ready["config_version"] == 3
    assert ready["transcriber_routes"] == ["google_stt"]
    assert app.state.registry.choose("transcriber").provider == "google_stt"


def test_bad_overlay_keeps_last_good_config(client, app):
    import asyncio

    src = app.state.config_source
    src.set("providers", {"limits": {"kill_switch": "not-a-bool-at-all", "velocity_calls": -3}})
    asyncio.run(app.state.config_service.refresh(force=True))
    assert client.get("/ready").json()["kill_switch"] is False


def test_prod_refuses_dev_auth_memory_store_and_fakes():
    s = make_settings(env="prod", phone_hash_pepper="p" * 40, stream_token_secret="s" * 40)
    problems = s.startup_problems()
    assert "AUTH_MODE must be firebase in prod" in problems
    assert "STORE must be firestore in prod" in problems
    assert "FAKE_PROVIDERS must be empty in prod" in problems
    with pytest.raises(RuntimeError), TestClient(create_app(s)):
        pass


def test_dev_auth_headers_are_refused_in_prod_even_if_reachable(app):
    """Belt and braces: require_user itself checks is_prod, not just the factory."""
    import asyncio
    from types import SimpleNamespace

    from fastapi import HTTPException

    from app.security.firebase_auth import require_user

    prod_settings = make_settings(env="prod")
    req = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(settings=prod_settings)), headers={}
    )
    with pytest.raises(HTTPException) as e:
        asyncio.run(require_user(req, "dev-0142", ENROLLED))
    assert e.value.status_code == 401
