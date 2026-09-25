"""Google OIDC verification for Cloud Scheduler calls to /internal/*."""

from __future__ import annotations

import asyncio

import structlog
from fastapi import HTTPException, Request

log = structlog.get_logger("oidc")


class SchedulerVerifier:
    def __init__(self, allowed_email: str, audience_base: str) -> None:
        self.allowed_email = allowed_email.strip().lower()
        self.audience_base = audience_base.rstrip("/")

    async def verify(self, token: str, path: str) -> str:
        from google.auth.transport import requests as g_requests
        from google.oauth2 import id_token as g_id_token

        audience = f"{self.audience_base}{path}"
        try:
            claims = await asyncio.to_thread(
                g_id_token.verify_oauth2_token, token, g_requests.Request(), audience
            )
        except Exception as e:  # noqa: BLE001
            log.warning("scheduler_token_rejected", error=type(e).__name__)
            raise HTTPException(401, "invalid token") from None
        email = str(claims.get("email", "")).lower()
        if not claims.get("email_verified") or email != self.allowed_email:
            log.warning("scheduler_token_wrong_caller", email=email)
            raise HTTPException(403, "forbidden")
        return email


class DevSchedulerVerifier:
    """Test double: accepts the literal token "dev-scheduler". Never used in prod."""

    async def verify(self, token: str, path: str) -> str:
        if token != "dev-scheduler":
            raise HTTPException(401, "invalid token")
        return "dev-scheduler@localhost"


async def require_scheduler(request: Request) -> str:
    settings = request.app.state.settings
    verifier = getattr(request.app.state, "scheduler_verifier", None)
    if verifier is None:
        raise HTTPException(404)
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise HTTPException(401, "missing bearer token")
    if settings.is_prod and isinstance(verifier, DevSchedulerVerifier):
        raise HTTPException(404)
    return await verifier.verify(header[7:].strip(), request.url.path)
