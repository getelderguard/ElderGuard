"""Phone number normalization and the peppered hash used as the only stored phone identifier."""

from __future__ import annotations

import hashlib
import hmac
import re

_DIGITS = re.compile(r"\D+")


def normalize_e164(raw: str | None) -> str | None:
    """Best-effort E.164 for US-centric input. Returns None for empty or anonymous callers."""
    if not raw:
        return None
    raw = raw.strip()
    if raw.lower() in {"anonymous", "restricted", "unknown", "private", "+266696687"}:
        return None
    digits = _DIGITS.sub("", raw)
    if not digits:
        return None
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    if 7 < len(digits) <= 15:
        return "+" + digits
    return None


def phone_hash(e164: str, pepper: str) -> str:
    return hmac.new(pepper.encode(), e164.encode(), hashlib.sha256).hexdigest()


def last4(e164: str) -> str:
    return e164[-4:]
