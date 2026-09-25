"""Push token registration. One device per uid; re-registering replaces it."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field

from app.api.deps import limiter
from app.security.firebase_auth import AuthUser, require_user
from app.sessions.models import Device

router = APIRouter(prefix="/v1/devices", tags=["devices"])


class DeviceBody(BaseModel):
    fcm_token: str = Field(min_length=20, max_length=512)
    platform: str = Field(pattern="^(ios|android)$")
    app_version: str = Field(default="", max_length=32)


@router.post("", status_code=204)
@limiter.limit("10/minute")
async def register(request: Request, body: DeviceBody, user: AuthUser = Depends(require_user)):
    await request.app.state.accounts.put_device(
        Device(
            uid=user.uid,
            fcm_token=body.fcm_token,
            platform=body.platform,
            app_version=body.app_version,
        )
    )
    return Response(status_code=204)


@router.delete("", status_code=204)
@limiter.limit("10/minute")
async def unregister(request: Request, user: AuthUser = Depends(require_user)):
    await request.app.state.accounts.delete_device(user.uid)
    return Response(status_code=204)
