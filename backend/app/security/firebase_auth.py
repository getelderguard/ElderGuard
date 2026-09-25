"""Caller identity for /v1 routes: Firebase ID tokens in prod, dev headers locally."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Protocol

import structlog
from fastapi import Header, HTTPException, Request

from app.security.phone import normalize_e164

log = structlog.get_logger("auth")


@dataclass(frozen=True)
class AuthUser:
    uid: str
    phone: str | None  # E.164 as verified by Firebase phone auth, or None
    claims: dict[str, Any] = field(default_factory=dict)

    @property
    def is_staff(self) -> bool:
        return bool(self.claims.get("staff") is True)


class TokenVerifier:
    """Verifies Firebase ID tokens. Kept behind a tiny interface so tests can swap it."""

    def __init__(self, project_id: str) -> None:
        import firebase_admin
        from firebase_admin import auth as fb_auth

        self._auth = fb_auth
        if not firebase_admin._apps:  # noqa: SLF001 - documented idiom
            firebase_admin.initialize_app(options={"projectId": project_id})

    async def verify(self, id_token: str) -> AuthUser:
        try:
            decoded = await asyncio.to_thread(
                self._auth.verify_id_token, id_token, check_revoked=False
            )
        except Exception as e:  # noqa: BLE001 - every failure is a 401
            log.info("id_token_rejected", error=type(e).__name__)
            raise HTTPException(401, "invalid token") from None
        uid = decoded.get("uid") or decoded.get("sub")
        if not uid:
            raise HTTPException(401, "invalid token")
        phone = normalize_e164(decoded.get("phone_number"))
        return AuthUser(uid=uid, phone=phone, claims=dict(decoded))


class IdentityAdmin(Protocol):
    async def delete_user(self, uid: str) -> None: ...


class NoopIdentityAdmin:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    async def delete_user(self, uid: str) -> None:
        self.deleted.append(uid)


class FirebaseIdentityAdmin:
    def __init__(self, project_id: str) -> None:
        import firebase_admin
        from firebase_admin import auth as fb_auth

        self._auth = fb_auth
        if not firebase_admin._apps:  # noqa: SLF001
            firebase_admin.initialize_app(options={"projectId": project_id})

    async def delete_user(self, uid: str) -> None:
        try:
            await asyncio.to_thread(self._auth.delete_user, uid)
        except self._auth.UserNotFoundError:
            return


def _bearer(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        token = header[7:].strip()
        return token or None
    return None


async def require_user(
    request: Request,
    x_dev_uid: str = Header(default=""),
    x_dev_phone: str = Header(default=""),
) -> AuthUser:
    settings = request.app.state.settings
    if settings.use_firebase_auth:
        token = _bearer(request)
        if token is None:
            raise HTTPException(401, "missing bearer token")
        verifier: TokenVerifier = request.app.state.token_verifier
        return await verifier.verify(token)

    if settings.is_prod:
        raise HTTPException(401, "dev auth is disabled")
    if not x_dev_uid:
        raise HTTPException(401, "X-Dev-Uid required in dev auth mode")
    phone = normalize_e164(x_dev_phone) if x_dev_phone else None
    claims = {"staff": True} if x_dev_uid.startswith("staff-") else {}
    return AuthUser(uid=x_dev_uid, phone=phone, claims=claims)


async def require_staff(
    request: Request,
    x_dev_uid: str = Header(default=""),
    x_dev_phone: str = Header(default=""),
) -> AuthUser:
    user = await require_user(request, x_dev_uid, x_dev_phone)
    if not user.is_staff:
        raise HTTPException(403, "staff only")
    return user
