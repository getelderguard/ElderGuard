"""Firestore back ends for sessions, accounts, usage, and config overlays.

Collections and fields are documented in docs/ARCHITECTURE.md. Nothing here stores transcript text.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

import structlog
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from app.providers.metrics import UsageEvent, estimate_cost
from app.sessions.accounts import AlreadyEnrolled, NotFound
from app.sessions.models import (
    SESSION_TTL_S,
    Account,
    Device,
    GuardianInvite,
    InitiatedBy,
    Session,
    SessionState,
)

log = structlog.get_logger("firestore")

USAGE_TTL_S = 90 * 86400
DELETION_TTL_S = 365 * 86400


def make_client(project: str) -> firestore.AsyncClient:
    return firestore.AsyncClient(project=project)


def _plain(value: Any) -> Any:
    """Firestore wants plain JSON-ish values; StrEnums and nested models become primitives."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(v) for v in value]
    if hasattr(value, "model_dump"):
        return _plain(value.model_dump())
    return value


def _expire_at(base_ts: float, ttl_s: float) -> datetime:
    return datetime.fromtimestamp(base_ts, tz=UTC) + timedelta(seconds=ttl_s)


class FirestoreSessionStore:
    def __init__(self, client: firestore.AsyncClient) -> None:
        self._db = client
        self._col = client.collection("sessions")

    async def create(self, session: Session) -> Session:
        data = _plain(session.model_dump())
        data["expire_at"] = _expire_at(session.created_at, SESSION_TTL_S)
        await self._col.document(session.id).set(data)
        return session

    async def get(self, session_id: str) -> Session | None:
        snap = await self._col.document(session_id).get()
        if not snap.exists:
            return None
        return self._to_session(snap.to_dict())

    async def get_by_call_sid(self, call_sid: str) -> Session | None:
        q = (
            self._col.where(filter=FieldFilter("call_sid", "==", call_sid))
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(1)
        )
        async for snap in q.stream():
            return self._to_session(snap.to_dict())
        return None

    async def find_pending_intent(self, phone_hash: str, now: float) -> Session | None:
        q = (
            self._col.where(filter=FieldFilter("phone_hash", "==", phone_hash))
            .where(filter=FieldFilter("state", "==", SessionState.PENDING.value))
            .where(filter=FieldFilter("expires_at", ">", now))
            .order_by("expires_at", direction=firestore.Query.DESCENDING)
            .limit(1)
        )
        async for snap in q.stream():
            return self._to_session(snap.to_dict())
        return None

    async def update(self, session_id: str, **fields: Any) -> Session:
        data = _plain(fields)
        data["updated_at"] = time.time()
        await self._col.document(session_id).update(data)
        session = await self.get(session_id)
        if session is None:
            raise KeyError(session_id)
        return session

    async def minutes_today(self, account_id: str, initiated_by: InitiatedBy, now: float) -> float:
        q = (
            self._col.where(filter=FieldFilter("account_id", "==", account_id))
            .where(filter=FieldFilter("initiated_by", "==", initiated_by.value))
            .where(filter=FieldFilter("created_at", ">=", now - 86400))
        )
        total = 0.0
        async for snap in q.stream():
            s = self._to_session(snap.to_dict())
            if s.duration_s:
                total += s.duration_s
            elif s.live_at and s.state in {SessionState.LIVE, SessionState.RECONNECTING}:
                total += now - s.live_at
        return total / 60.0

    async def inbound_count_since(self, phone_hash: str, since: float) -> int:
        q = self._col.where(filter=FieldFilter("phone_hash", "==", phone_hash)).where(
            filter=FieldFilter("created_at", ">=", since)
        )
        count = 0
        async for snap in q.stream():
            if snap.get("call_sid"):
                count += 1
        return count

    async def expire_stale(self, now: float) -> int:
        q = self._col.where(filter=FieldFilter("state", "==", SessionState.PENDING.value)).where(
            filter=FieldFilter("expires_at", "<=", now)
        )
        count = 0
        async for snap in q.stream():
            await snap.reference.update(
                {"state": SessionState.EXPIRED.value, "updated_at": time.time()}
            )
            count += 1
        return count

    async def abandon_stale(self, now: float, max_age_s: float) -> int:
        """Sessions that never got a terminal status callback (backend restart, Twilio blip)."""
        count = 0
        for state in (SessionState.RINGING, SessionState.LIVE, SessionState.RECONNECTING):
            q = self._col.where(filter=FieldFilter("state", "==", state.value)).where(
                filter=FieldFilter("created_at", "<=", now - max_age_s)
            )
            async for snap in q.stream():
                s = self._to_session(snap.to_dict())
                await snap.reference.update(
                    {
                        "state": SessionState.ENDED.value,
                        "ended_at": now,
                        "duration_s": s.duration_s or ((now - s.live_at) if s.live_at else 0.0),
                        "funnel": {**s.funnel, "swept_at": now},
                        "updated_at": now,
                    }
                )
                count += 1
        return count

    async def recent(self, limit: int = 50) -> list[Session]:
        q = self._col.order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
        out = [self._to_session(snap.to_dict()) async for snap in q.stream()]
        out.reverse()
        return out

    async def recent_for_account(self, account_id: str, limit: int = 20) -> list[Session]:
        q = (
            self._col.where(filter=FieldFilter("account_id", "==", account_id))
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        return [self._to_session(snap.to_dict()) async for snap in q.stream()]

    async def delete_for_account(self, account_id: str) -> int:
        q = self._col.where(filter=FieldFilter("account_id", "==", account_id))
        count = 0
        async for snap in q.stream():
            await snap.reference.delete()
            count += 1
        return count

    @staticmethod
    def _to_session(data: dict[str, Any]) -> Session:
        data = dict(data)
        data.pop("expire_at", None)
        return Session.model_validate(data)


class FirestoreAccountRepo:
    def __init__(self, client: firestore.AsyncClient) -> None:
        self._db = client
        self._accounts = client.collection("accounts")
        self._index = client.collection("phone_index")
        self._invites = client.collection("guardian_invites")
        self._devices = client.collection("devices")

    async def by_phone_hash(self, h: str) -> Account | None:
        snap = await self._index.document(h).get()
        if not snap.exists or snap.get("role") != "senior":
            return None
        return await self.get(snap.get("account_id"))

    async def get(self, account_id: str) -> Account | None:
        snap = await self._accounts.document(account_id).get()
        return Account.model_validate(snap.to_dict()) if snap.exists else None

    async def for_senior_uid(self, uid: str) -> Account | None:
        return await self.get(uid)

    async def guarded_by(self, uid: str) -> list[Account]:
        q = self._accounts.where(filter=FieldFilter("guardian_uids", "array_contains", uid))
        return [Account.model_validate(s.to_dict()) async for s in q.stream()]

    async def create(self, account: Account) -> Account:
        if (await self._index.document(account.phone_hash).get()).exists:
            raise AlreadyEnrolled(account.id)
        if (await self._accounts.document(account.id).get()).exists:
            raise AlreadyEnrolled(account.id)
        batch = self._db.batch()
        batch.set(self._accounts.document(account.id), _plain(account.model_dump()))
        batch.set(
            self._index.document(account.phone_hash),
            {"account_id": account.id, "role": "senior", "uid": account.senior.uid},
        )
        await batch.commit()
        return account

    async def update(self, account_id: str, **fields: Any) -> Account:
        data = _plain(fields)
        data["updated_at"] = time.time()
        try:
            await self._accounts.document(account_id).update(data)
        except Exception as e:  # noqa: BLE001 - NotFound from the client
            raise NotFound(account_id) from e
        account = await self.get(account_id)
        if account is None:
            raise NotFound(account_id)
        return account

    async def create_invite(self, invite: GuardianInvite) -> GuardianInvite:
        data = _plain(invite.model_dump())
        data["expire_at"] = _expire_at(invite.expires_at, 0)
        await self._invites.document(invite.id).set(data)
        return invite

    async def open_invite_for_phone(self, h: str, now: float) -> GuardianInvite | None:
        q = (
            self._invites.where(filter=FieldFilter("phone_hash", "==", h))
            .where(filter=FieldFilter("claimed_at", "==", None))
            .where(filter=FieldFilter("expires_at", ">", now))
            .order_by("expires_at", direction=firestore.Query.DESCENDING)
            .limit(1)
        )
        async for snap in q.stream():
            data = dict(snap.to_dict())
            data.pop("expire_at", None)
            return GuardianInvite.model_validate(data)
        return None

    async def claim_invite(self, invite_id: str, uid: str, now: float) -> None:
        await self._invites.document(invite_id).update({"claimed_at": now, "claimed_uid": uid})

    async def put_device(self, device: Device) -> None:
        await self._devices.document(device.uid).set(_plain(device.model_dump()))

    async def get_device(self, uid: str) -> Device | None:
        snap = await self._devices.document(uid).get()
        return Device.model_validate(snap.to_dict()) if snap.exists else None

    async def delete_device(self, uid: str) -> None:
        await self._devices.document(uid).delete()

    async def delete_account(self, account_id: str) -> None:
        acct = await self.get(account_id)
        if acct is None:
            return
        batch = self._db.batch()
        batch.delete(self._accounts.document(account_id))
        batch.delete(self._index.document(acct.phone_hash))
        batch.delete(self._devices.document(acct.senior.uid))
        q = self._invites.where(filter=FieldFilter("account_id", "==", account_id))
        async for snap in q.stream():
            batch.delete(snap.reference)
        await batch.commit()

    async def record_deletion(self, record: dict[str, Any]) -> None:
        data = dict(record)
        data["expire_at"] = _expire_at(float(record.get("at", time.time())), DELETION_TTL_S)
        await self._db.collection("deletions").add(data)


class FirestoreUsageSink:
    """One document per provider call, plus monthly rollups for the grant report."""

    def __init__(self, client: firestore.AsyncClient) -> None:
        self._db = client
        self._events = client.collection("usage_events")
        self._monthly = client.collection("usage_monthly")

    async def emit(self, event: UsageEvent) -> None:
        if event.est_cost_usd == 0.0:
            event.est_cost_usd = estimate_cost(event.provider, event.model, event.usage)
        data = _plain(event.model_dump())
        data["expire_at"] = _expire_at(event.ts, USAGE_TTL_S)
        await self._events.add(data)

    async def events_between(self, start: float, end: float) -> list[UsageEvent]:
        q = self._events.where(filter=FieldFilter("ts", ">=", start)).where(
            filter=FieldFilter("ts", "<", end)
        )
        out = []
        async for snap in q.stream():
            data = dict(snap.to_dict())
            data.pop("expire_at", None)
            out.append(UsageEvent.model_validate(data))
        return out

    async def write_rollup(self, month: str, rollup: dict[str, Any]) -> None:
        await self._monthly.document(month).set(_plain(rollup))

    async def read_rollup(self, month: str) -> dict[str, Any] | None:
        snap = await self._monthly.document(month).get()
        return snap.to_dict() if snap.exists else None


class FirestoreConfigSource:
    """Reads config/{doc} overlay documents. Writes go through infra/scripts, never the API."""

    def __init__(self, client: firestore.AsyncClient) -> None:
        self._config = client.collection("config")

    async def read(self, doc: str) -> dict[str, Any] | None:
        snap = await self._config.document(doc).get()
        return snap.to_dict() if snap.exists else None
