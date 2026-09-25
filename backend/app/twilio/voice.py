"""Guardian Line voice webhooks: inbound, reconnect, call status, stream status."""

from __future__ import annotations

import time

import structlog
from fastapi import APIRouter, Depends, Request, Response

from app.security.phone import normalize_e164, phone_hash
from app.security.stream_token import make_stream_token
from app.security.twilio_signature import twilio_form
from app.sessions.models import InitiatedBy, Session, SessionState
from app.telephony import twiml

log = structlog.get_logger("voice")

router = APIRouter(prefix="/twilio/voice", tags=["twilio"])

TERMINAL_STATUSES = {"completed", "busy", "failed", "no-answer", "canceled"}


def _xml(body: str) -> Response:
    return Response(content=body, media_type="application/xml")


def _urls(request: Request) -> dict[str, str]:
    base = request.app.state.settings.public_base_url.rstrip("/")
    ws_base = base.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
    return {
        "ws": f"{ws_base}/twilio/media",
        "redirect": f"{base}/twilio/voice/reconnect",
        "status": f"{base}/twilio/voice/stream-status",
    }


@router.post("/inbound")
async def inbound(request: Request, form: dict[str, str] = Depends(twilio_form)) -> Response:
    state = request.app.state
    settings = state.settings
    limits = state.provider_config.limits
    now = time.time()
    call_sid = form.get("CallSid", "")

    if limits.kill_switch:
        log.warning("inbound_rejected", reason="kill_switch")
        return _xml(twiml.reject())

    e164 = normalize_e164(form.get("From"))
    if not e164:
        log.info("inbound_rejected", reason="anonymous")
        return _xml(twiml.reject())
    h = phone_hash(e164, settings.phone_hash_pepper.get_secret_value())

    account = await state.accounts.by_phone_hash(h)
    if account is None:
        log.info("inbound_rejected", reason="unknown_number")
        return _xml(twiml.reject())

    recent = await state.session_store.inbound_count_since(h, now - limits.velocity_window_seconds)
    if recent >= limits.velocity_calls:
        log.warning("inbound_rejected", reason="velocity", account_id=account.id)
        return _xml(twiml.reject())

    pending = await state.session_store.find_pending_intent(h, now)
    if pending is not None:
        used = await state.session_store.minutes_today(account.id, InitiatedBy.APP, now)
        if used >= limits.daily_minutes_per_account:
            log.warning("inbound_rejected", reason="daily_cap_app", account_id=account.id)
            return _xml(twiml.reject())
        session = await state.session_store.update(
            pending.id,
            state=SessionState.RINGING,
            call_sid=call_sid,
            funnel={**pending.funnel, "inbound_at": now},
        )
    else:
        used = await state.session_store.minutes_today(account.id, InitiatedBy.LINE, now)
        if used >= limits.line_initiated_daily_minutes:
            log.warning("inbound_rejected", reason="daily_cap_line", account_id=account.id)
            return _xml(twiml.reject())
        session = await state.session_store.create(
            Session(
                account_id=account.id,
                phone_hash=h,
                state=SessionState.RINGING,
                initiated_by=InitiatedBy.LINE,
                call_sid=call_sid,
                funnel={"inbound_at": now},
            )
        )

    token = make_stream_token(settings.stream_token_secret.get_secret_value(), session.id, call_sid)
    urls = _urls(request)
    log.info(
        "inbound_accepted",
        session_id=session.id,
        initiated_by=session.initiated_by,
        account_id=account.id,
    )
    return _xml(
        twiml.guardian_line(
            ws_url=urls["ws"],
            session_id=session.id,
            token=token,
            redirect_url=urls["redirect"],
            status_callback_url=urls["status"],
        )
    )


@router.post("/reconnect")
async def reconnect(request: Request, form: dict[str, str] = Depends(twilio_form)) -> Response:
    state = request.app.state
    limits = state.provider_config.limits
    call_sid = form.get("CallSid", "")
    session = await state.session_store.get_by_call_sid(call_sid)
    if session is None or session.state not in {SessionState.LIVE, SessionState.RECONNECTING}:
        return _xml(twiml.fallback_notice())
    if session.reconnect_attempts >= limits.max_reconnect_attempts:
        log.warning("reconnect_exhausted", session_id=session.id)
        return _xml(twiml.fallback_notice())
    session = await state.session_store.update(
        session.id,
        state=SessionState.RECONNECTING,
        reconnect_attempts=session.reconnect_attempts + 1,
        stream_sid=None,
    )
    token = make_stream_token(
        state.settings.stream_token_secret.get_secret_value(), session.id, call_sid
    )
    urls = _urls(request)
    log.info("reconnect_issued", session_id=session.id, attempt=session.reconnect_attempts)
    return _xml(
        twiml.guardian_line(
            ws_url=urls["ws"],
            session_id=session.id,
            token=token,
            redirect_url=urls["redirect"],
            status_callback_url=urls["status"],
            instruction_text=None,
        )
    )


@router.post("/status")
async def status(request: Request, form: dict[str, str] = Depends(twilio_form)) -> Response:
    state = request.app.state
    call_status = form.get("CallStatus", "")
    call_sid = form.get("CallSid", "")
    session = await state.session_store.get_by_call_sid(call_sid)
    if session is not None and call_status in TERMINAL_STATUSES:
        now = time.time()
        duration = float(form.get("CallDuration", "0") or 0)
        if not duration and session.live_at:
            duration = now - session.live_at
        await state.session_store.update(
            session.id, state=SessionState.ENDED, ended_at=now, duration_s=duration
        )
        log.info("call_ended", session_id=session.id, call_status=call_status, duration_s=duration)
    return Response(status_code=204)


@router.post("/stream-status")
async def stream_status(request: Request, form: dict[str, str] = Depends(twilio_form)) -> Response:
    state = request.app.state
    event = form.get("StreamEvent", "")
    call_sid = form.get("CallSid", "")
    session = await state.session_store.get_by_call_sid(call_sid)
    if session is not None:
        key = {"stream-started": "stream_started_at", "stream-stopped": "stream_stopped_at"}.get(
            event
        )
        funnel = dict(session.funnel)
        if key:
            funnel[key] = time.time()
        if event == "stream-error":
            funnel["stream_error_at"] = time.time()
        await state.session_store.update(session.id, funnel=funnel)
    log.info("stream_status", event=event, error=form.get("StreamError"))
    return Response(status_code=204)
