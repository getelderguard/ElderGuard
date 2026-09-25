from __future__ import annotations

from tests.conftest import ENROLLED, STRANGER, twilio_post


def _inbound(client, from_number: str, call_sid: str = "CA123", sign: bool = True):
    return twilio_post(
        client,
        "/twilio/voice/inbound",
        {"From": from_number, "To": "+14155550100", "CallSid": call_sid, "CallStatus": "ringing"},
        sign=sign,
    )


def test_bad_signature_is_403(client):
    assert _inbound(client, ENROLLED, sign=False).status_code == 403


def test_unknown_number_rejected_silently(client):
    r = _inbound(client, STRANGER)
    assert r.status_code == 200
    assert "<Reject" in r.text
    assert "<Say" not in r.text


def test_anonymous_caller_rejected(client):
    r = _inbound(client, "anonymous")
    assert "<Reject" in r.text


def test_enrolled_number_gets_stream(client):
    r = _inbound(client, ENROLLED, call_sid="CA1")
    assert r.status_code == 200
    assert "<Connect>" in r.text and "<Stream" in r.text
    assert 'name="sid"' in r.text and 'name="tok"' in r.text
    assert "<Redirect" in r.text
    sessions = client.get("/v1/sessions").json()
    assert len(sessions) == 1
    assert sessions[0]["state"] == "ringing"
    assert sessions[0]["initiated_by"] == "line"


def test_intent_promotes_to_app_session(client):
    r = client.post("/v1/sessions/intent", headers={"X-Dev-Phone": ENROLLED})
    assert r.status_code == 200
    sid = r.json()["session_id"]
    assert r.json()["guardian_line_number"] == "+14155550100"
    r2 = _inbound(client, ENROLLED, call_sid="CA2")
    assert f'value="{sid}"' in r2.text
    s = client.get(f"/v1/sessions/{sid}").json()
    assert s["state"] == "ringing" and s["initiated_by"] == "app"


def test_intent_rejects_unenrolled(client):
    assert client.post("/v1/sessions/intent", headers={"X-Dev-Phone": STRANGER}).status_code == 403


def test_velocity_limit(client):
    for i in range(3):
        assert "<Connect>" in _inbound(client, ENROLLED, call_sid=f"CA{i}").text
    assert "<Reject" in _inbound(client, ENROLLED, call_sid="CA99").text


def test_status_ends_session(client):
    _inbound(client, ENROLLED, call_sid="CA5")
    r = twilio_post(
        client,
        "/twilio/voice/status",
        {"CallSid": "CA5", "CallStatus": "completed", "CallDuration": "42"},
    )
    assert r.status_code == 204
    s = client.get("/v1/sessions").json()[-1]
    assert s["state"] == "ended"


def test_reconnect_only_for_live_sessions(client):
    _inbound(client, ENROLLED, call_sid="CA7")
    r = twilio_post(client, "/twilio/voice/reconnect", {"CallSid": "CA7"})
    assert "<Hangup" in r.text  # session is only ringing, never went live
    r = twilio_post(client, "/twilio/voice/reconnect", {"CallSid": "nope"})
    assert "<Hangup" in r.text


def test_health_and_ready(client):
    assert client.get("/health").json() == {"status": "ok"}
    ready = client.get("/ready").json()
    assert ready["fake_providers"] is True
    assert ready["scorer_routes"]
