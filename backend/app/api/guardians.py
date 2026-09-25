"""Guardian linking. Invite from the senior's phone; complete from the guardian's own phone."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.api.deps import limiter, senior_account
from app.security.firebase_auth import AuthUser, require_user
from app.security.phone import normalize_e164
from app.sessions.accounts import AccountError, NotFound
from app.sessions.models import GUARDIAN_COOL_OFF_S

router = APIRouter(prefix="/v1/guardians", tags=["guardians"])

RELATIONSHIPS = {
    "son",
    "daughter",
    "spouse",
    "sibling",
    "grandchild",
    "friend",
    "caregiver",
    "family",
}


class InviteBody(BaseModel):
    phone: str = Field(min_length=7, max_length=20)
    name: str = Field(min_length=1, max_length=40)
    relationship: str = Field(default="family", max_length=20)


@router.post("/invite", status_code=201)
@limiter.limit("3/hour")
async def invite(request: Request, body: InviteBody, user: AuthUser = Depends(require_user)):
    account = await senior_account(request, user)
    e164 = normalize_e164(body.phone)
    if not e164:
        raise HTTPException(400, "phone must be a valid number")
    rel = body.relationship.strip().lower()
    if rel not in RELATIONSHIPS:
        rel = "family"
    try:
        inv = await request.app.state.account_service.invite_guardian(
            account, phone_e164=e164, name=body.name.strip(), relationship=rel
        )
    except AccountError as e:
        raise HTTPException(400, str(e)) from None
    return {
        "invite_id": inv.id,
        "expires_at": inv.expires_at,
        "cool_off_seconds": GUARDIAN_COOL_OFF_S,
    }


@router.post("/link")
@limiter.limit("5/hour")
async def link(request: Request, user: AuthUser = Depends(require_user)):
    """No body on purpose: the only input is the phone number the guardian proved they own."""
    if not user.phone:
        raise HTTPException(400, "sign in with a phone number first")
    state = request.app.state
    try:
        account, guardian = await state.account_service.link_guardian(
            uid=user.uid, phone_e164=user.phone
        )
    except NotFound:
        raise HTTPException(404, "no invitation for this phone number") from None
    except AccountError as e:
        raise HTTPException(400, str(e)) from None
    await state.notify.guardian_linked(account, guardian)
    return {
        "account_id": account.id,
        "senior_nickname": account.senior.nickname,
        "active_at": guardian.active_at,
    }


@router.delete("/accounts/{account_id}", status_code=204)
@limiter.limit("10/hour")
async def unlink(request: Request, account_id: str, user: AuthUser = Depends(require_user)):
    """A guardian removes themselves. The senior removes guardians from their own profile."""
    state = request.app.state
    account = await state.accounts.get(account_id)
    if account is None or user.uid not in account.guardian_uids:
        raise HTTPException(404)
    await state.account_service.remove_guardian(account, user.uid)
    return Response(status_code=204)


@router.get("/accounts")
@limiter.limit("30/minute")
async def guarded_accounts(request: Request, user: AuthUser = Depends(require_user)):
    accounts = await request.app.state.accounts.guarded_by(user.uid)
    out = []
    for a in accounts:
        me = next((g for g in a.guardians if g.uid == user.uid), None)
        out.append(
            {
                "account_id": a.id,
                "senior_nickname": a.senior.nickname,
                "senior_display_name": a.senior.display_name,
                "active": bool(me and me.is_active()),
                "active_at": me.active_at if me else None,
            }
        )
    return out
