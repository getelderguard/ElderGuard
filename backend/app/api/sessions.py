"""Session endpoints for the app: declare an intent to dial, watch a session, give feedback."""

from __future__ import annotations

import time

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.api.deps import limiter, readable_account, senior_account
from app.security.firebase_auth import AuthUser, require_user
from app.sessions.models import InitiatedBy, Session, SessionState

log = structlog.get_logger("sessions")

router = APIRouter(prefix="/v1/sessions", tags=["sessions"])

FEEDBACK_NOTES = {"", "false_alarm", "was_a_scam", "not_sure", "merge_failed", "no_alert"}


class FeedbackBody(BaseModel):
    false_alarm: bool
    note: str = ""


@router.post("/intent", status_code=201)
@limiter.limit("5/minute")
async def create_intent(request: Request, user: AuthUser = Depends(require_user)) -> dict:
    """The app is about to dial the Guardian Line from the senior's phone."""
    state = request.app.state
    settings = state.settings
    account = await senior_account(request, user)
    config = await state.config_service.get_config()
    if config.limits.kill_switch:
        raise HTTPException(503, "ElderGuard is paused right now")
    now = time.time()
    used = await state.session_store.minutes_today(account.id, InitiatedBy.APP, now)
    if used >= config.limits.daily_minutes_per_account:
        raise HTTPException(429, "daily listening limit reached")
    session = await state.session_store.create(
        Session(
            account_id=account.id,
            phone_hash=account.phone_hash,
            state=SessionState.PENDING,
            initiated_by=InitiatedBy.APP,
            expires_at=now + config.limits.intent_ttl_seconds,
            funnel={"intent_at": now},
        )
    )
    log.info("intent_created", session_id=session.id, account_id=account.id)
    return {
        "session_id": session.id,
        "guardian_line_number": settings.twilio_guardian_number,
        "expires_at": session.expires_at,
    }


@router.get("")
@limiter.limit("30/minute")
async def list_sessions(request: Request, user: AuthUser = Depends(require_user)) -> list[dict]:
    state = request.app.state
    account = await state.accounts.for_senior_uid(user.uid)
    if account is None:
        guarded = await state.accounts.guarded_by(user.uid)
        guarded = [a for a in guarded if a.can_read(user.uid)]
        if not guarded:
            raise HTTPException(404, "not enrolled")
        account = guarded[0]
    sessions = await state.session_store.recent_for_account(account.id, 20)
    return [s.public_view() for s in sessions]


@router.get("/{session_id}")
@limiter.limit("60/minute")
async def get_session(request: Request, session_id: str, user: AuthUser = Depends(require_user)):
    session = await request.app.state.session_store.get(session_id)
    if session is None:
        raise HTTPException(404)
    await readable_account(request, user, session.account_id)
    return session.public_view()


@router.post("/{session_id}/feedback", status_code=204)
@limiter.limit("10/minute")
async def feedback(
    request: Request,
    session_id: str,
    body: FeedbackBody,
    user: AuthUser = Depends(require_user),
):
    state = request.app.state
    session = await state.session_store.get(session_id)
    if session is None:
        raise HTTPException(404)
    await readable_account(request, user, session.account_id)
    note = body.note if body.note in FEEDBACK_NOTES else "other"
    await state.session_store.update(
        session_id,
        funnel={**session.funnel, "feedback_at": time.time()},
        takeover={**session.takeover, "feedback": {"false_alarm": body.false_alarm, "note": note}},
    )
    log.info("session_feedback", session_id=session_id, false_alarm=body.false_alarm, note=note)
    return None
