"""Runs only against the Firestore emulator (FIRESTORE_EMULATOR_HOST). CI starts one."""

from __future__ import annotations

import asyncio
import os
import time
import uuid

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("FIRESTORE_EMULATOR_HOST"), reason="needs the Firestore emulator"
)


@pytest.fixture
def fs():
    from app.persistence.firestore import make_client

    return make_client(os.environ.get("GCP_PROJECT", "demo-elderguard"))


def test_session_round_trip_and_queries(fs):
    from app.persistence.firestore import FirestoreSessionStore
    from app.sessions.models import InitiatedBy, Session, SessionState

    store = FirestoreSessionStore(fs)
    h = "h-" + uuid.uuid4().hex
    now = time.time()

    async def run():
        pending = await store.create(
            Session(account_id="a1", phone_hash=h, expires_at=now + 60, funnel={"intent_at": now})
        )
        assert (await store.find_pending_intent(h, now)).id == pending.id
        live = await store.update(
            pending.id, state=SessionState.RINGING, call_sid="CA-" + h, funnel={"inbound_at": now}
        )
        assert live.state == SessionState.RINGING
        assert (await store.get_by_call_sid("CA-" + h)).id == pending.id
        assert await store.inbound_count_since(h, now - 10) == 1
        await store.update(pending.id, state=SessionState.LIVE, live_at=now)
        assert await store.minutes_today("a1", InitiatedBy.APP, now + 120) >= 2.0
        assert await store.abandon_stale(now + 5000, 3000) >= 1
        assert (await store.get(pending.id)).state == SessionState.ENDED
        assert [s.id for s in await store.recent_for_account("a1", 5)][0] == pending.id

    asyncio.run(run())


def test_account_and_invite_round_trip(fs):
    from app.persistence.firestore import FirestoreAccountRepo
    from app.sessions.accounts import AccountService, AlreadyEnrolled
    from app.sessions.models import Device
    from tests.conftest import make_settings

    repo = FirestoreAccountRepo(fs)
    svc = AccountService(repo, make_settings())
    uid = "u-" + uuid.uuid4().hex[:8]
    phone = "+1415555" + uuid.uuid4().hex[:4].translate(str.maketrans("abcdef", "012345"))

    async def run():
        acct = await svc.enroll(
            uid=uid,
            phone_e164=phone,
            display_name="Rosa",
            nickname="Mom",
            consent_version="v",
            watch_list=["IRS"],
        )
        assert (await repo.by_phone_hash(acct.phone_hash)).id == uid
        with pytest.raises(AlreadyEnrolled):
            await repo.create(acct)
        gphone = "+1415555" + uuid.uuid4().hex[:4].translate(str.maketrans("abcdef", "012345"))
        await svc.invite_guardian(acct, phone_e164=gphone, name="Kid", relationship="son")
        account, guardian = await svc.link_guardian(uid="g-" + uid, phone_e164=gphone)
        assert guardian.uid in account.guardian_uids
        assert [a.id for a in await repo.guarded_by("g-" + uid)] == [uid]
        await repo.put_device(Device(uid=uid, fcm_token="t" * 40))
        assert (await repo.get_device(uid)).fcm_token == "t" * 40
        await repo.delete_device(uid)
        assert await repo.get_device(uid) is None

    asyncio.run(run())


def test_usage_and_config(fs):
    from app.persistence.firestore import FirestoreConfigSource, FirestoreUsageSink
    from app.providers.base import Usage
    from app.providers.metrics import UsageEvent

    sink = FirestoreUsageSink(fs)
    src = FirestoreConfigSource(fs)
    ts = time.time()

    async def run():
        await sink.emit(
            UsageEvent(
                ts=ts,
                capability="scorer",
                provider="anthropic",
                model="claude-sonnet-5",
                usage=Usage(input_tokens=10),
            )
        )
        events = await sink.events_between(ts - 1, ts + 1)
        assert any(e.provider == "anthropic" for e in events)
        await sink.write_rollup("2000-01", {"total_cost_usd": 1.5})
        assert (await sink.read_rollup("2000-01"))["total_cost_usd"] == 1.5
        assert await src.read("nope-" + uuid.uuid4().hex) is None

    asyncio.run(run())
