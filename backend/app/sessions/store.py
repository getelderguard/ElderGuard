"""Session persistence. In-memory for dev and tests; app.persistence.firestore for prod."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Protocol

from app.sessions.models import InitiatedBy, Session, SessionState


class SessionStore(Protocol):
    async def create(self, session: Session) -> Session: ...

    async def get(self, session_id: str) -> Session | None: ...

    async def get_by_call_sid(self, call_sid: str) -> Session | None: ...

    async def find_pending_intent(self, phone_hash: str, now: float) -> Session | None: ...

    async def update(self, session_id: str, **fields: Any) -> Session: ...

    async def minutes_today(
        self, account_id: str, initiated_by: InitiatedBy, now: float
    ) -> float: ...

    async def inbound_count_since(self, phone_hash: str, since: float) -> int: ...

    async def expire_stale(self, now: float) -> int: ...

    async def abandon_stale(self, now: float, max_age_s: float) -> int: ...

    async def recent(self, limit: int = 50) -> list[Session]: ...

    async def recent_for_account(self, account_id: str, limit: int = 20) -> list[Session]: ...

    async def delete_for_account(self, account_id: str) -> int: ...


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = asyncio.Lock()

    async def create(self, session: Session) -> Session:
        async with self._lock:
            self._sessions[session.id] = session
        return session

    async def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    async def get_by_call_sid(self, call_sid: str) -> Session | None:
        for s in reversed(list(self._sessions.values())):
            if s.call_sid == call_sid:
                return s
        return None

    async def find_pending_intent(self, phone_hash: str, now: float) -> Session | None:
        for s in reversed(list(self._sessions.values())):
            if (
                s.phone_hash == phone_hash
                and s.state == SessionState.PENDING
                and s.expires_at is not None
                and s.expires_at > now
            ):
                return s
        return None

    async def update(self, session_id: str, **fields: Any) -> Session:
        async with self._lock:
            current = self._sessions[session_id]
            data = current.model_dump()
            data.update(fields)
            data["updated_at"] = time.time()
            updated = Session.model_validate(data)
            self._sessions[session_id] = updated
        return updated

    async def minutes_today(self, account_id: str, initiated_by: InitiatedBy, now: float) -> float:
        day_start = now - 86400
        total = 0.0
        for s in self._sessions.values():
            if s.account_id != account_id or s.initiated_by != initiated_by:
                continue
            if s.created_at < day_start:
                continue
            if s.duration_s:
                total += s.duration_s
            elif s.live_at and s.state in {SessionState.LIVE, SessionState.RECONNECTING}:
                total += now - s.live_at
        return total / 60.0

    async def inbound_count_since(self, phone_hash: str, since: float) -> int:
        return sum(
            1
            for s in self._sessions.values()
            if s.phone_hash == phone_hash and s.call_sid is not None and s.created_at >= since
        )

    async def expire_stale(self, now: float) -> int:
        count = 0
        for s in list(self._sessions.values()):
            if s.state == SessionState.PENDING and s.expires_at is not None and s.expires_at <= now:
                await self.update(s.id, state=SessionState.EXPIRED)
                count += 1
        return count

    async def abandon_stale(self, now: float, max_age_s: float) -> int:
        count = 0
        active = {SessionState.RINGING, SessionState.LIVE, SessionState.RECONNECTING}
        for s in list(self._sessions.values()):
            if s.state in active and s.created_at <= now - max_age_s:
                duration = s.duration_s or ((now - s.live_at) if s.live_at else 0.0)
                await self.update(
                    s.id,
                    state=SessionState.ENDED,
                    ended_at=now,
                    duration_s=duration,
                    funnel={**s.funnel, "swept_at": now},
                )
                count += 1
        return count

    async def recent(self, limit: int = 50) -> list[Session]:
        return list(self._sessions.values())[-limit:]

    async def recent_for_account(self, account_id: str, limit: int = 20) -> list[Session]:
        mine = [s for s in self._sessions.values() if s.account_id == account_id]
        return list(reversed(mine))[:limit]

    async def delete_for_account(self, account_id: str) -> int:
        ids = [s.id for s in self._sessions.values() if s.account_id == account_id]
        for sid in ids:
            self._sessions.pop(sid, None)
        return len(ids)
