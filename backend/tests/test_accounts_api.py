"""Enrolment, profile, guardian linking, devices. All through dev auth headers."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.main import create_app
from app.sessions.models import CONSENT_VERSION, GUARDIAN_COOL_OFF_S
from tests.conftest import GUARDIAN_HEADERS, SENIOR_HEADERS, STAFF_HEADERS, make_settings

NEW_SENIOR = {"X-Dev-Uid": "uid-new", "X-Dev-Phone": "+14155550123"}
NEW_GUARDIAN = {"X-Dev-Uid": "uid-kid", "X-Dev-Phone": "+14155550321"}
ENROLL = {
    "display_name": "Rosa",
    "nickname": "Mom",
    "consent_version": CONSENT_VERSION,
    "watch_list": ["Medicare", " gift cards ", "Medicare"],
}


def test_enroll_then_me(client):
    r = client.post("/v1/accounts/me", json=ENROLL, headers=NEW_SENIOR)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["id"] == "uid-new"
    assert body["senior"]["phone_last4"] == "0123"
    assert body["watch_list"] == ["Medicare", "gift cards"]  # trimmed and deduped
    assert body["senior"]["consent_version"] == CONSENT_VERSION
    assert client.get("/v1/accounts/me", headers=NEW_SENIOR).json()["id"] == "uid-new"


def test_enroll_requires_phone_and_current_consent(client):
    r = client.post("/v1/accounts/me", json=ENROLL, headers={"X-Dev-Uid": "uid-nophone"})
    assert r.status_code == 400
    r = client.post(
        "/v1/accounts/me", json={**ENROLL, "consent_version": "2000-01-01"}, headers=NEW_SENIOR
    )
    assert r.status_code == 409


def test_enroll_is_invite_only_when_a_list_is_set():
    app = create_app(make_settings(enroll_allowed_phones="+14155550999"))
    with TestClient(app) as c:
        r = c.post("/v1/accounts/me", json=ENROLL, headers=NEW_SENIOR)
        assert r.status_code == 403
        invited = {"X-Dev-Uid": "uid-invited", "X-Dev-Phone": "+14155550999"}
        assert c.post("/v1/accounts/me", json=ENROLL, headers=invited).status_code == 201


def test_prod_enrolment_is_closed_by_default():
    assert not make_settings(env="prod").may_enroll("+14155550123")
    assert make_settings(env="prod", enroll_allowed_phones="+14155550123").may_enroll(
        "+14155550123"
    )
    assert make_settings().may_enroll("+14155550123")  # dev and tests stay open


def test_enroll_twice_is_conflict(client):
    assert client.post("/v1/accounts/me", json=ENROLL, headers=NEW_SENIOR).status_code == 201
    assert client.post("/v1/accounts/me", json=ENROLL, headers=NEW_SENIOR).status_code == 409
    # same phone, different uid: the phone index is the identity
    other = {"X-Dev-Uid": "uid-other", "X-Dev-Phone": "+14155550123"}
    assert client.post("/v1/accounts/me", json=ENROLL, headers=other).status_code == 409


def test_unauthenticated_and_unenrolled(client):
    assert client.get("/v1/accounts/me").status_code == 401
    assert client.get("/v1/accounts/me", headers={"X-Dev-Uid": "nobody"}).status_code == 404


def test_patch_profile(client):
    r = client.patch(
        "/v1/accounts/me",
        json={
            "nickname": "Abuela",
            "watch_list": ["IRS"],
            "settings": {"announcement": True, "spoken_takeover": False, "alert_guardian": True},
            "caller_id_visible": True,
        },
        headers=SENIOR_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["senior"]["nickname"] == "Abuela"
    assert body["watch_list"] == ["IRS"]
    assert body["settings"]["spoken_takeover"] is False
    assert body["senior"]["caller_id_visible"] is True


def test_guardian_link_flow_with_cool_off(client, app):
    client.post("/v1/accounts/me", json=ENROLL, headers=NEW_SENIOR)
    r = client.post(
        "/v1/guardians/invite",
        json={"phone": "(415) 555-0321", "name": "Daniel", "relationship": "son"},
        headers=NEW_SENIOR,
    )
    assert r.status_code == 201, r.text
    assert r.json()["cool_off_seconds"] == GUARDIAN_COOL_OFF_S

    # A phone with no invite gets nothing.
    assert client.post("/v1/guardians/link", headers=GUARDIAN_HEADERS).status_code == 404

    before = time.time()
    r = client.post("/v1/guardians/link", headers=NEW_GUARDIAN)
    assert r.status_code == 200, r.text
    assert r.json()["account_id"] == "uid-new"
    assert r.json()["active_at"] >= before + GUARDIAN_COOL_OFF_S - 1

    acct = client.get("/v1/accounts/me", headers=NEW_SENIOR).json()
    assert acct["guardians"][0]["uid"] == "uid-kid"
    assert acct["guardians"][0]["active"] is False

    mine = client.get("/v1/guardians/accounts", headers=NEW_GUARDIAN).json()
    assert mine[0]["account_id"] == "uid-new" and mine[0]["active"] is False

    # The senior's phone was told a guardian was added.
    kinds = [p.kind for _, p in app.state.push_sender.sent]
    assert "guardian_linked" not in kinds  # no device registered yet, so nothing sent
    client.post(
        "/v1/devices",
        json={"fcm_token": "x" * 40, "platform": "ios", "app_version": "1.0.0"},
        headers=NEW_SENIOR,
    )
    r = client.post(
        "/v1/guardians/invite",
        json={"phone": "+14155550444", "name": "Ana", "relationship": "daughter"},
        headers=NEW_SENIOR,
    )
    assert r.status_code == 201
    r = client.post(
        "/v1/guardians/link", headers={"X-Dev-Uid": "uid-ana", "X-Dev-Phone": "+14155550444"}
    )
    assert r.status_code == 200
    kinds = [p.kind for _, p in app.state.push_sender.sent]
    assert "guardian_linked" in kinds


def test_senior_cannot_become_own_guardian(client):
    client.post("/v1/accounts/me", json=ENROLL, headers=NEW_SENIOR)
    r = client.post(
        "/v1/guardians/invite",
        json={"phone": "+14155550123", "name": "Me", "relationship": "son"},
        headers=NEW_SENIOR,
    )
    assert r.status_code == 400


def test_link_from_seniors_own_uid_is_refused(client):
    """A scammer who has the senior's unlocked phone cannot add themselves from it."""
    client.post("/v1/accounts/me", json=ENROLL, headers=NEW_SENIOR)
    client.post(
        "/v1/guardians/invite",
        json={"phone": "+14155550321", "name": "Daniel", "relationship": "son"},
        headers=NEW_SENIOR,
    )
    # Same uid as the senior, but somehow presenting the guardian's phone: refused.
    r = client.post(
        "/v1/guardians/link", headers={"X-Dev-Uid": "uid-new", "X-Dev-Phone": "+14155550321"}
    )
    assert r.status_code == 400


def test_inactive_guardian_cannot_read_sessions(client):
    client.post("/v1/accounts/me", json=ENROLL, headers=NEW_SENIOR)
    client.post(
        "/v1/guardians/invite",
        json={"phone": "+14155550321", "name": "Daniel", "relationship": "son"},
        headers=NEW_SENIOR,
    )
    client.post("/v1/guardians/link", headers=NEW_GUARDIAN)
    sid = client.post("/v1/sessions/intent", headers=NEW_SENIOR).json()["session_id"]
    assert client.get(f"/v1/sessions/{sid}", headers=NEW_SENIOR).status_code == 200
    assert client.get(f"/v1/sessions/{sid}", headers=NEW_GUARDIAN).status_code == 404  # cool-off
    assert client.get(f"/v1/sessions/{sid}", headers=GUARDIAN_HEADERS).status_code == 404


def test_seeded_guardian_reads_sessions_and_stranger_does_not(client):
    sid = client.post("/v1/sessions/intent", headers=SENIOR_HEADERS).json()["session_id"]
    assert client.get(f"/v1/sessions/{sid}", headers=GUARDIAN_HEADERS).status_code == 200
    assert client.get(f"/v1/sessions/{sid}", headers=STAFF_HEADERS).status_code == 404


def test_devices_validate(client):
    bad = {"fcm_token": "short", "platform": "ios"}
    assert client.post("/v1/devices", json=bad, headers=SENIOR_HEADERS).status_code == 422
    bad = {"fcm_token": "x" * 40, "platform": "web"}
    assert client.post("/v1/devices", json=bad, headers=SENIOR_HEADERS).status_code == 422
    ok = {"fcm_token": "x" * 40, "platform": "android", "app_version": "1.0.0"}
    assert client.post("/v1/devices", json=ok, headers=SENIOR_HEADERS).status_code == 204
    assert client.delete("/v1/devices", headers=SENIOR_HEADERS).status_code == 204


def test_session_feedback(client):
    sid = client.post("/v1/sessions/intent", headers=SENIOR_HEADERS).json()["session_id"]
    r = client.post(
        f"/v1/sessions/{sid}/feedback",
        json={"false_alarm": True, "note": "not_sure"},
        headers=SENIOR_HEADERS,
    )
    assert r.status_code == 204
    r = client.post(
        f"/v1/sessions/{sid}/feedback", json={"false_alarm": False}, headers=STAFF_HEADERS
    )
    assert r.status_code == 404


def test_consent_version_endpoint(client):
    assert client.get("/v1/accounts/consent-version").json()["consent_version"] == CONSENT_VERSION


def test_delete_account_removes_everything(client, app):
    client.post("/v1/accounts/me", json=ENROLL, headers=NEW_SENIOR)
    client.post("/v1/devices", json={"fcm_token": "x" * 40, "platform": "ios"}, headers=NEW_SENIOR)
    sid = client.post("/v1/sessions/intent", headers=NEW_SENIOR).json()["session_id"]
    assert client.delete("/v1/accounts/me", headers=NEW_SENIOR).status_code == 204
    assert client.get("/v1/accounts/me", headers=NEW_SENIOR).status_code == 404
    assert client.get(f"/v1/sessions/{sid}", headers=NEW_SENIOR).status_code == 404
    assert app.state.identity.deleted == ["uid-new"]
    record = app.state.accounts.deletions[0]
    assert record["reason"] == "self_service" and "uid-new" not in str(record)
    # The phone is free to enrol again (a new uid after re-verifying the number).
    again = {"X-Dev-Uid": "uid-again", "X-Dev-Phone": "+14155550123"}
    assert client.post("/v1/accounts/me", json=ENROLL, headers=again).status_code == 201


def test_guardian_can_unlink_self(client):
    client.post("/v1/accounts/me", json=ENROLL, headers=NEW_SENIOR)
    client.post(
        "/v1/guardians/invite",
        json={"phone": "+14155550321", "name": "Daniel", "relationship": "son"},
        headers=NEW_SENIOR,
    )
    client.post("/v1/guardians/link", headers=NEW_GUARDIAN)
    assert client.delete("/v1/guardians/accounts/uid-new", headers=NEW_GUARDIAN).status_code == 204
    assert client.get("/v1/guardians/accounts", headers=NEW_GUARDIAN).json() == []
    assert client.get("/v1/accounts/me", headers=NEW_SENIOR).json()["guardians"] == []
    assert client.delete("/v1/guardians/accounts/uid-new", headers=NEW_GUARDIAN).status_code == 404
