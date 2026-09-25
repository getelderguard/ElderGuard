"""Validate X-Twilio-Signature against the configured public URL, never the observed host."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from twilio.request_validator import RequestValidator

from app.settings import Settings


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


async def twilio_form(
    request: Request, settings: Settings = Depends(get_settings)
) -> dict[str, str]:
    """Parses the form body and rejects the request unless Twilio's signature matches."""
    token = settings.twilio_auth_token
    if token is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Twilio auth token not configured")
    form = await request.form()
    params = {k: str(v) for k, v in form.items()}
    url = settings.public_base_url.rstrip("/") + request.url.path
    if request.url.query:
        url += "?" + request.url.query
    signature = request.headers.get("X-Twilio-Signature", "")
    if not RequestValidator(token.get_secret_value()).validate(url, params, signature):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid Twilio signature")
    return params
