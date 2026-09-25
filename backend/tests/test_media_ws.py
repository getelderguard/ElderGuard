"""End-to-end media stream with fake providers: audio in, scripted scam out, tier moves."""

from __future__ import annotations

import base64
import time

from app.security.stream_token import make_stream_token
from app.telephony.codec import silence
from tests.conftest import ENROLLED, SENIOR_HEADERS, newest_session_id, twilio_post

FRAME = base64.b64encode(silence(0.02)).decode()  # one 20 ms mulaw frame


def _start_session(client, call_sid: str = "CA-ws-1") -> tuple[str, str]:
    r = twilio_post(
        client,
        "/twilio/voice/inbound",
        {"From": ENROLLED, "To": "+14155550100", "CallSid": call_sid, "CallStatus": "in-progress"},
    )
    assert "<Connect>" in r.text
    session_id = newest_session_id(client)
    token = make_stream_token("test-stream-secret", session_id, call_sid)
    return session_id, token


def _start_msg(session_id: str, token: str, call_sid: str = "CA-ws-1") -> dict:
    return {
        "event": "start",
        "sequenceNumber": "1",
        "start": {
            "streamSid": "MZ-1",
            "accountSid": "AC-1",
            "callSid": call_sid,
            "tracks": ["inbound"],
            "customParameters": {"sid": session_id, "tok": token},
            "mediaFormat": {"encoding": "audio/x-mulaw", "sampleRate": 8000, "channels": 1},
        },
        "streamSid": "MZ-1",
    }


def _send_audio(ws, seconds: float) -> None:
    frames = int(seconds / 0.02)
    for i in range(frames):
        ws.send_json(
            {
                "event": "media",
                "sequenceNumber": str(i + 2),
                "media": {
                    "track": "inbound",
                    "chunk": str(i + 1),
                    "timestamp": str(i * 20),
                    "payload": FRAME,
                },
                "streamSid": "MZ-1",
            }
        )


def test_scripted_scam_moves_the_dial(client, app):
    session_id, token = _start_session(client)
    with client.websocket_connect("/twilio/media") as ws:
        ws.send_json({"event": "connected", "protocol": "Call", "version": "1.0.0"})
        ws.send_json(_start_msg(session_id, token))
        _send_audio(ws, 35.0)  # the fake transcriber emits one scripted line per 5 s of audio
        deadline = time.time() + 3.0
        while time.time() < deadline:
            s = client.get(f"/v1/sessions/{session_id}", headers=SENIOR_HEADERS).json()
            if s["max_score"] >= 7:
                break
            time.sleep(0.05)
        ws.send_json({"event": "stop", "streamSid": "MZ-1", "stop": {"callSid": "CA-ws-1"}})

    s = client.get(f"/v1/sessions/{session_id}", headers=SENIOR_HEADERS).json()
    assert s["state"] == "live"  # the status callback, not the stream, ends a session
    assert s["max_score"] >= 7
    assert s["tier"] in {"caution", "stop"}
    assert s["dial"] > 35
    assert "UNUSUAL_PAYMENT" in s["flags"] or "INFO_FISHING" in s["flags"]
    assert session_id not in app.state.live_calls

    events = app.state.usage_sink.events
    assert any(e.capability == "scorer" for e in events)
    transcriber_events = [e for e in events if e.capability == "transcriber"]
    assert transcriber_events and transcriber_events[0].usage.audio_seconds >= 34.0


def test_bad_token_never_goes_live(client, app):
    session_id, _ = _start_session(client, call_sid="CA-ws-2")
    with client.websocket_connect("/twilio/media") as ws:
        ws.send_json({"event": "connected"})
        ws.send_json(_start_msg(session_id, "bogus:99999999999", call_sid="CA-ws-2"))
        try:
            ws.receive_text()
        except Exception:  # noqa: BLE001 - the server closes the socket
            pass
    s = client.get(f"/v1/sessions/{session_id}", headers=SENIOR_HEADERS).json()
    assert s["state"] == "ringing"
    assert session_id not in app.state.live_calls


def test_no_audio_flags_session(client, app):
    session_id, token = _start_session(client, call_sid="CA-ws-3")
    with client.websocket_connect("/twilio/media") as ws:
        ws.send_json({"event": "connected"})
        ws.send_json(_start_msg(session_id, token, call_sid="CA-ws-3"))
        _send_audio(ws, 2.0)  # under the 5 s the fake transcriber needs for its first line
        deadline = time.time() + 3.0
        while time.time() < deadline:
            if (
                client.get(f"/v1/sessions/{session_id}", headers=SENIOR_HEADERS).json()["tier"]
                == "no_audio"
            ):
                break
            time.sleep(0.05)
        ws.send_json({"event": "stop", "streamSid": "MZ-1"})
    assert (
        client.get(f"/v1/sessions/{session_id}", headers=SENIOR_HEADERS).json()["tier"]
        == "no_audio"
    )


def test_failing_providers_report_unknown(app, settings):
    from fastapi.testclient import TestClient

    from app.main import create_app
    from tests.conftest import make_settings

    failing = create_app(make_settings(fake_providers="fail"))
    with TestClient(failing) as c:
        session_id, token = _start_session(c, call_sid="CA-ws-4")
        with c.websocket_connect("/twilio/media") as ws:
            ws.send_json({"event": "connected"})
            ws.send_json(_start_msg(session_id, token, call_sid="CA-ws-4"))
            try:
                ws.receive_text()
            except Exception:  # noqa: BLE001
                pass
        s = c.get(f"/v1/sessions/{session_id}", headers=SENIOR_HEADERS).json()
        assert s["tier"] == "unknown"
        assert s["state"] == "ringing"
