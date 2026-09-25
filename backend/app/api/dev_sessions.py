"""Dev-only session endpoints until Firebase Auth lands in M1. Disabled entirely in prod."""

from __future__ import annotations

import time

from fastapi import APIRouter, Header, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.security.phone import normalize_e164, phone_hash
from app.sessions.models import InitiatedBy, Session, SessionState

router = APIRouter(prefix="/v1/sessions", tags=["sessions"])
limiter = Limiter(key_func=get_remote_address)


def _dev_only(request: Request) -> None:
    if request.app.state.settings.is_prod:
        raise HTTPException(404)


@router.post("/intent")
@limiter.limit("5/minute")
async def create_intent(request: Request, x_dev_phone: str = Header(default="")) -> dict:
    """Registers that the app is about to dial the Guardian Line from this phone."""
    _dev_only(request)
    state = request.app.state
    settings = state.settings
    e164 = normalize_e164(x_dev_phone)
    if not e164:
        raise HTTPException(400, "X-Dev-Phone must be an E.164 number")
    h = phone_hash(e164, settings.phone_hash_pepper.get_secret_value())
    account = await state.accounts.by_phone_hash(h)
    if account is None:
        raise HTTPException(403, "phone not enrolled")
    now = time.time()
    ttl = state.provider_config.limits.intent_ttl_seconds
    session = await state.session_store.create(
        Session(
            account_id=account.id,
            phone_hash=h,
            state=SessionState.PENDING,
            initiated_by=InitiatedBy.APP,
            expires_at=now + ttl,
            funnel={"intent_at": now},
        )
    )
    return {
        "session_id": session.id,
        "guardian_line_number": settings.twilio_guardian_number,
        "expires_at": session.expires_at,
    }


@router.get("/{session_id}")
async def get_session(request: Request, session_id: str) -> dict:
    _dev_only(request)
    session = await request.app.state.session_store.get(session_id)
    if session is None:
        raise HTTPException(404)
    return session.public_view()


@router.get("")
async def list_sessions(request: Request) -> list[dict]:
    _dev_only(request)
    sessions = await request.app.state.session_store.recent(50)
    return [s.public_view() for s in sessions]
