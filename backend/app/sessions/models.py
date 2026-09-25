"""Session and account records. No transcript text is ever stored on a session."""

from __future__ import annotations

import secrets
import time
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.providers.base import RedFlag
from app.scoring.tiers import Tier


class SessionState(StrEnum):
    PENDING = "pending"
    RINGING = "ringing"
    LIVE = "live"
    RECONNECTING = "reconnecting"
    ENDED = "ended"
    EXPIRED = "expired"


class InitiatedBy(StrEnum):
    APP = "app"
    LINE = "line"


def new_session_id() -> str:
    return "s_" + secrets.token_urlsafe(12)


class Session(BaseModel):
    id: str = Field(default_factory=new_session_id)
    account_id: str
    phone_hash: str
    state: SessionState = SessionState.PENDING
    initiated_by: InitiatedBy = InitiatedBy.APP
    call_sid: str | None = None
    stream_sid: str | None = None
    created_at: float = Field(default_factory=time.time)
    expires_at: float | None = None
    live_at: float | None = None
    ended_at: float | None = None
    duration_s: float | None = None
    score: int | None = None
    dial: float = 0.0
    tier: Tier = Tier.LISTENING
    flags: list[RedFlag] = Field(default_factory=list)
    reason: str = ""
    max_score: int = 0
    updated_at: float = Field(default_factory=time.time)
    reconnect_attempts: int = 0
    provider_choices: dict[str, str] = Field(default_factory=dict)
    takeover: dict[str, Any] = Field(default_factory=dict)
    funnel: dict[str, float] = Field(default_factory=dict)
    transcript_stored: bool = False

    def public_view(self) -> dict[str, Any]:
        """What the app is allowed to see. Reason text is for guardians, not the senior."""
        return {
            "id": self.id,
            "state": self.state,
            "initiated_by": self.initiated_by,
            "tier": self.tier,
            "dial": self.dial,
            "score": self.score,
            "flags": [f.value for f in self.flags],
            "max_score": self.max_score,
            "updated_at": self.updated_at,
            "live_at": self.live_at,
            "ended_at": self.ended_at,
        }


class Account(BaseModel):
    id: str
    phone_hash: str
    senior_nickname: str = "Mom"
    guardian_name: str = "your family"
    watch_list: list[str] = Field(default_factory=list)
