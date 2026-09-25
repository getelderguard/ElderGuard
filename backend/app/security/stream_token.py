"""Short-lived HMAC token that binds a media WebSocket to one session and one Twilio call."""

from __future__ import annotations

import hashlib
import hmac
import time

TOKEN_TTL_SECONDS = 300


def make_stream_token(secret: str, session_id: str, call_sid: str, now: float | None = None) -> str:
    exp = int((now if now is not None else time.time()) + TOKEN_TTL_SECONDS)
    return f"{_digest(secret, session_id, call_sid, exp)}:{exp}"


def verify_stream_token(
    secret: str, token: str | None, session_id: str, call_sid: str, now: float | None = None
) -> bool:
    if not token or ":" not in token:
        return False
    digest, _, exp_text = token.rpartition(":")
    try:
        exp = int(exp_text)
    except ValueError:
        return False
    if exp < (now if now is not None else time.time()):
        return False
    expected = _digest(secret, session_id, call_sid, exp)
    return hmac.compare_digest(digest, expected)


def _digest(secret: str, session_id: str, call_sid: str, exp: int) -> str:
    msg = f"{session_id}:{call_sid}:{exp}".encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
