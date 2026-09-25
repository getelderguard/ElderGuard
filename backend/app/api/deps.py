"""Shared pieces for /v1 routers: the rate limiter and the "which account is this?" helpers."""

from __future__ import annotations

import hashlib

from fastapi import HTTPException, Request
from slowapi import Limiter

from app.security.firebase_auth import AuthUser
from app.sessions.models import Account


def _rate_key(request: Request) -> str:
    """Per-user where we can tell, per-address otherwise. Never the raw token."""
    dev_uid = request.headers.get("x-dev-uid")
    if dev_uid:
        return "uid:" + dev_uid
    auth = request.headers.get("authorization", "")
    if auth:
        return "tok:" + hashlib.sha256(auth.encode()).hexdigest()[:24]
    client = request.client.host if request.client else "unknown"
    return "ip:" + client


limiter = Limiter(key_func=_rate_key)


async def senior_account(request: Request, user: AuthUser) -> Account:
    account = await request.app.state.accounts.for_senior_uid(user.uid)
    if account is None:
        raise HTTPException(404, "not enrolled")
    return account


async def readable_account(request: Request, user: AuthUser, account_id: str) -> Account:
    account = await request.app.state.accounts.get(account_id)
    if account is None or not account.can_read(user.uid):
        raise HTTPException(404)
    return account
