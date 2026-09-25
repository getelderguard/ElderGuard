"""Staff-only read endpoints. Writes to config happen through infra/scripts, not here."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Request

from app.api.deps import limiter
from app.api.internal import run_rollup
from app.providers.metrics import month_of, previous_month
from app.security.firebase_auth import AuthUser, require_staff

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/usage")
@limiter.limit("30/minute")
async def usage(request: Request, user: AuthUser = Depends(require_staff)) -> dict[str, object]:
    state = request.app.state
    current = month_of(time.time())
    last = previous_month(current)
    mtd = await run_rollup(state, current)
    prev = await state.usage_sink.read_rollup(last) or await run_rollup(state, last)
    config = await state.config_service.get_config()
    return {
        "month_to_date": mtd,
        "last_month": prev,
        "routing": {
            cap: [r.model_dump() for r in config.routing(cap).routes] for cap in config.capabilities
        },
        "limits": config.limits.model_dump(),
        "flags": (await state.config_service.get_flags()).model_dump(),
    }
