"""Senior enrolment and profile. The phone number always comes from the verified token."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.api.deps import limiter, senior_account
from app.security.firebase_auth import AuthUser, require_user
from app.sessions.accounts import AlreadyEnrolled
from app.sessions.models import CONSENT_VERSION, AccountSettings

log = structlog.get_logger("accounts")

router = APIRouter(prefix="/v1/accounts", tags=["accounts"])


class EnrollBody(BaseModel):
    display_name: str = Field(min_length=1, max_length=60)
    nickname: str = Field(default="Mom", min_length=1, max_length=30)
    consent_version: str = Field(min_length=1, max_length=20)
    watch_list: list[str] = Field(default_factory=list, max_length=12)


class PatchBody(BaseModel):
    nickname: str | None = Field(default=None, min_length=1, max_length=30)
    watch_list: list[str] | None = Field(default=None, max_length=12)
    settings: AccountSettings | None = None
    carrier_capability: dict[str, str | int | float | bool] | None = None
    caller_id_visible: bool | None = None


def _clean_watch_list(items: list[str]) -> list[str]:
    cleaned = [w.strip()[:40] for w in items if w and w.strip()]
    return list(dict.fromkeys(cleaned))[:12]


@router.post("/me", status_code=201)
@limiter.limit("3/minute")
async def enroll(request: Request, body: EnrollBody, user: AuthUser = Depends(require_user)):
    if not user.phone:
        raise HTTPException(400, "sign in with a phone number first")
    if not request.app.state.settings.may_enroll(user.phone):
        # Pre-launch: only invited numbers reach the paid call path. Counsel reviews first.
        log.info("enroll_not_invited")
        raise HTTPException(403, "enrolment is invite-only for now")
    if body.consent_version != CONSENT_VERSION:
        raise HTTPException(409, f"consent version {CONSENT_VERSION} required")
    service = request.app.state.account_service
    try:
        account = await service.enroll(
            uid=user.uid,
            phone_e164=user.phone,
            display_name=body.display_name.strip(),
            nickname=body.nickname.strip(),
            consent_version=body.consent_version,
            watch_list=_clean_watch_list(body.watch_list),
        )
    except AlreadyEnrolled:
        raise HTTPException(409, "already enrolled") from None
    return account.public_view()


@router.get("/me")
@limiter.limit("30/minute")
async def me(request: Request, user: AuthUser = Depends(require_user)):
    account = await senior_account(request, user)
    return account.public_view()


@router.patch("/me")
@limiter.limit("30/minute")
async def patch_me(request: Request, body: PatchBody, user: AuthUser = Depends(require_user)):
    account = await senior_account(request, user)
    fields: dict = {}
    if body.nickname is not None:
        fields["senior"] = {**account.senior.model_dump(), "nickname": body.nickname.strip()}
    if body.carrier_capability is not None or body.caller_id_visible is not None:
        senior = fields.get("senior", account.senior.model_dump())
        if body.carrier_capability is not None:
            senior["carrier_capability"] = body.carrier_capability
        if body.caller_id_visible is not None:
            senior["caller_id_visible"] = body.caller_id_visible
        fields["senior"] = senior
    if body.watch_list is not None:
        fields["watch_list"] = _clean_watch_list(body.watch_list)
    if body.settings is not None:
        fields["settings"] = body.settings.model_dump()
    if not fields:
        return account.public_view()
    updated = await request.app.state.accounts.update(account.id, **fields)
    return updated.public_view()


@router.delete("/me", status_code=204)
@limiter.limit("3/hour")
async def delete_me(request: Request, user: AuthUser = Depends(require_user)):
    """Everything goes: account, phone index, devices, invites, sessions, the auth user.

    Usage events keep their account_id (a random uid, not a phone) until their 90-day TTL so
    the month's grant report still adds up. Nothing in them identifies a person.
    """
    state = request.app.state
    account = await senior_account(request, user)
    for call in list(state.live_calls.values()):
        if call.session is not None and call.session.account_id == account.id:
            raise HTTPException(409, "a call is in progress")
    await state.session_store.delete_for_account(account.id)
    await state.account_service.delete_account(account, reason="self_service")
    await state.identity.delete_user(user.uid)
    return Response(status_code=204)


@router.get("/consent-version")
async def consent_version() -> dict[str, str]:
    return {"consent_version": CONSENT_VERSION}
