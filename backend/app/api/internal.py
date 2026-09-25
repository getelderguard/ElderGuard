"""Cloud Scheduler targets. Authenticated by a Google OIDC token from the scheduler SA."""

from __future__ import annotations

import time

import structlog
from fastapi import APIRouter, Depends, Request

from app.providers.metrics import month_bounds, month_of, previous_month, rollup_events
from app.security.oidc import require_scheduler

log = structlog.get_logger("internal")

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/sweep")
async def sweep(request: Request, caller: str = Depends(require_scheduler)) -> dict[str, int]:
    state = request.app.state
    now = time.time()
    config = await state.config_service.get_config()
    expired = await state.session_store.expire_stale(now)
    abandoned = await state.session_store.abandon_stale(
        now, config.limits.max_session_minutes * 60 + 300
    )
    log.info("sweep", expired=expired, abandoned=abandoned, caller=caller)
    return {"expired": expired, "abandoned": abandoned}


async def run_rollup(state, month: str) -> dict:  # noqa: ANN001
    start, end = month_bounds(month)
    events = await state.usage_sink.events_between(start, end)
    rollup = rollup_events(month, events, time.time())
    await state.usage_sink.write_rollup(month, rollup)
    return rollup


@router.post("/rollup")
async def rollup(request: Request, caller: str = Depends(require_scheduler)) -> dict[str, object]:
    state = request.app.state
    current = month_of(time.time())
    months = [previous_month(current), current]
    out = {}
    for m in months:
        r = await run_rollup(state, m)
        out[m] = {"total_cost_usd": r["total_cost_usd"], "events": r["events"]}
    log.info("rollup", months=months, caller=caller)
    return out
