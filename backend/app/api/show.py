"""Show Me: check a pasted message or a screenshot. Processed in memory and never stored."""

from __future__ import annotations

import asyncio
import base64
import binascii

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.deps import limiter, senior_account
from app.providers.base import (
    ProviderError,
    RedFlag,
    ShowAnswers,
    ShowInput,
)
from app.providers.metrics import UsageEvent
from app.scoring.verdict import Verdict, verdict_for
from app.security.firebase_auth import AuthUser, require_user

log = structlog.get_logger("show")

router = APIRouter(prefix="/v1/show", tags=["show"])

MAX_TEXT_CHARS = 4000
MAX_ANSWER_CHARS = 200
MAX_IMAGE_BYTES = 3_500_000
# Base64 is 4 chars per 3 bytes; the JSON body adds a little. Anything bigger is refused before
# it is parsed.
MAX_BODY_BYTES = MAX_IMAGE_BYTES * 4 // 3 + 20_000
CHECK_TIMEOUT_S = 25.0


class CheckBody(BaseModel):
    text: str = Field(default="", max_length=MAX_TEXT_CHARS)
    image_b64: str | None = Field(default=None, max_length=MAX_BODY_BYTES)
    who_is_it_from: str = Field(default="", max_length=MAX_ANSWER_CHARS)
    what_do_they_want: str = Field(default="", max_length=MAX_ANSWER_CHARS)


class CheckOut(BaseModel):
    """Nothing the model wrote reaches the senior: a stranger can steer that text."""

    verdict: Verdict
    flags: list[str]


def sniff_image(data: bytes) -> str | None:
    """The media type from the file's own bytes. The client's claim is never trusted."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return None


def _decode_image(b64: str) -> tuple[str, str]:
    try:
        raw = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(422, "image is not valid base64") from None
    if not raw:
        raise HTTPException(422, "image is empty")
    if len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "image is too large")
    media_type = sniff_image(raw)
    if media_type is None:
        raise HTTPException(415, "unsupported image type")
    return media_type, base64.b64encode(raw).decode("ascii")


@router.post("/check")
@limiter.limit("10/minute;60/hour")
async def check(
    request: Request, body: CheckBody, user: AuthUser = Depends(require_user)
) -> CheckOut:
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        raise HTTPException(413, "request is too large")

    state = request.app.state
    await senior_account(request, user)
    config = await state.config_service.get_config()
    flags = await state.config_service.get_flags()
    if config.limits.kill_switch or not flags.show_me:
        raise HTTPException(503, "Show Me is paused right now")

    text = body.text.strip()
    if not text and not body.image_b64:
        raise HTTPException(422, "send some text or a picture")

    media_type: str | None = None
    image_b64: str | None = None
    if body.image_b64:
        media_type, image_b64 = _decode_image(body.image_b64)

    inp = ShowInput(
        kind="image" if image_b64 else "text",
        text=text,
        image_media_type=media_type,
        image_b64=image_b64,
    )
    answers = ShowAnswers(
        who_is_it_from=body.who_is_it_from.strip(), what_do_they_want=body.what_do_they_want.strip()
    )

    registry = state.registry
    try:
        chain = registry.chain("message_analyzer")
    except ProviderError as e:
        log.error("show_no_provider", error=str(e))
        raise HTTPException(503, "Show Me is unavailable right now") from None

    for route in chain:
        try:
            analyzer = await asyncio.to_thread(registry.build, "message_analyzer", route)
            result = await analyzer.analyze(inp, answers, timeout_s=CHECK_TIMEOUT_S)
        except ProviderError as e:
            log.warning("show_provider_failed", provider=route.provider, error=type(e).__name__)
            await state.usage_sink.emit(
                UsageEvent(
                    account_id=user.uid,
                    capability="message_analyzer",
                    provider=route.provider,
                    model=route.model,
                    ok=False,
                )
            )
            continue
        await state.usage_sink.emit(
            UsageEvent(
                account_id=user.uid,
                capability="message_analyzer",
                provider=result.provider,
                model=result.model,
                usage=result.usage,
                latency_ms=result.latency_ms,
            )
        )
        verdict = verdict_for(result.score, result.red_flags)
        # Metadata only: no message text, no image, no model reasoning.
        log.info(
            "show_checked",
            kind=inp.kind,
            verdict=verdict,
            score=result.score,
            flags=[f.value for f in result.red_flags],
            provider=result.provider,
        )
        return CheckOut(verdict=verdict, flags=_public_flags(result.red_flags))

    # Every provider failed. Say so; never fall back to a calm answer.
    raise HTTPException(503, "Show Me could not check this right now")


def _public_flags(flags: list[RedFlag]) -> list[str]:
    return [f.value for f in flags]
