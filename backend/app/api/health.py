"""Liveness must stay dependency-free so the uptime check measures the service, not Firestore."""

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request) -> dict[str, object]:
    state = request.app.state
    registry = state.registry
    config = await state.config_service.get_config()
    return {
        "status": "ok",
        "env": state.settings.env,
        "store": state.settings.store,
        "auth_mode": state.settings.auth_mode,
        "notify": state.settings.notify,
        "fake_providers": state.settings.fakes_enabled,
        "scorer_routes": [r.provider for r in registry.available_routes("scorer")],
        "transcriber_routes": [r.provider for r in registry.available_routes("transcriber")],
        "config_version": config.version,
        "kill_switch": config.limits.kill_switch,
        "live_calls": len(state.live_calls),
    }
