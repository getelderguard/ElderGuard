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


GUARDIAN_COOL_OFF_S = 24 * 3600
INVITE_TTL_S = 7 * 86400
SESSION_TTL_S = 30 * 86400
CONSENT_VERSION = "2026-09-25"


class Senior(BaseModel):
    uid: str
    display_name: str = ""
    nickname: str = "Mom"
    phone_last4: str = ""
    consent_version: str = ""
    consent_at: float | None = None
    carrier_capability: dict[str, Any] = Field(default_factory=dict)
    caller_id_visible: bool | None = None


class Guardian(BaseModel):
    uid: str
    name: str
    relationship: str = "family"
    phone_last4: str = ""
    linked_at: float = Field(default_factory=time.time)
    active_at: float = Field(default_factory=time.time)

    def is_active(self, now: float | None = None) -> bool:
        return (now or time.time()) >= self.active_at


class AccountSettings(BaseModel):
    announcement: bool = True
    spoken_takeover: bool = True
    alert_guardian: bool = True


class Account(BaseModel):
    """One senior, their guardians, and their preferences. id == the senior's uid."""

    id: str
    phone_hash: str
    senior: Senior
    guardians: list[Guardian] = Field(default_factory=list)
    guardian_uids: list[str] = Field(default_factory=list)
    watch_list: list[str] = Field(default_factory=list)
    settings: AccountSettings = Field(default_factory=AccountSettings)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    @property
    def senior_nickname(self) -> str:
        return self.senior.nickname or "Mom"

    @property
    def guardian_name(self) -> str:
        active = self.active_guardians()
        return active[0].name if active else "your family"

    def active_guardians(self, now: float | None = None) -> list[Guardian]:
        return [g for g in self.guardians if g.is_active(now)]

    def can_read(self, uid: str, now: float | None = None) -> bool:
        if uid == self.senior.uid:
            return True
        return any(g.uid == uid and g.is_active(now) for g in self.guardians)

    def public_view(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "senior": {
                "uid": self.senior.uid,
                "display_name": self.senior.display_name,
                "nickname": self.senior.nickname,
                "phone_last4": self.senior.phone_last4,
                "consent_version": self.senior.consent_version,
                "caller_id_visible": self.senior.caller_id_visible,
            },
            "guardians": [
                {
                    "uid": g.uid,
                    "name": g.name,
                    "relationship": g.relationship,
                    "phone_last4": g.phone_last4,
                    "active_at": g.active_at,
                    "active": g.is_active(),
                }
                for g in self.guardians
            ],
            "watch_list": self.watch_list,
            "settings": self.settings.model_dump(),
        }


class GuardianInvite(BaseModel):
    id: str = Field(default_factory=lambda: "gi_" + secrets.token_urlsafe(9))
    account_id: str
    phone_hash: str
    name: str
    relationship: str = "family"
    created_at: float = Field(default_factory=time.time)
    expires_at: float = Field(default_factory=lambda: time.time() + INVITE_TTL_S)
    claimed_at: float | None = None
    claimed_uid: str | None = None


class Device(BaseModel):
    uid: str
    fcm_token: str
    platform: str = "ios"
    app_version: str = ""
    updated_at: float = Field(default_factory=time.time)
