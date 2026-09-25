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
    return {
        "status": "ok",
        "env": state.settings.env,
        "fake_providers": state.settings.fakes_enabled,
        "scorer_routes": [r.provider for r in registry.available_routes("scorer")],
        "transcriber_routes": [r.provider for r in registry.available_routes("transcriber")],
        "kill_switch": state.provider_config.limits.kill_switch,
    }
