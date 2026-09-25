"""Twilio Media Streams WebSocket: audio in, transcript to the scorer, tiers to the session."""

from __future__ import annotations

import asyncio
import base64
import json
import time

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.providers.base import AudioFormat, ProviderError, StreamingTranscriber, Usage
from app.providers.metrics import UsageEvent
from app.scoring.rolling import CadencePolicy, RollingScorer, ScoreUpdate
from app.scoring.tiers import Tier
from app.security.stream_token import verify_stream_token
from app.sessions.models import Session, SessionState

log = structlog.get_logger("media")

router = APIRouter(tags=["twilio"])

WS_POLICY_VIOLATION = 1008


class LiveCall:
    """One Twilio media stream bound to one session."""

    def __init__(self, ws: WebSocket) -> None:
        self.ws = ws
        self.app_state = ws.app.state
        self.settings = self.app_state.settings
        self.session: Session | None = None
        self.stream_sid: str | None = None
        self.transcriber: StreamingTranscriber | None = None
        self.scorer: RollingScorer | None = None
        self.tasks: list[asyncio.Task[None]] = []
        self.last_final_at: float | None = None
        self.no_audio_flagged = False
        self.frames = 0
        self.account = None

    async def handle(self, msg: dict) -> bool:
        """Returns False when the stream should close."""
        event = msg.get("event")
        if event == "connected":
            return True
        if event == "start":
            return await self._on_start(msg.get("start") or {})
        if event == "media":
            await self._on_media(msg.get("media") or {})
            return True
        if event == "stop":
            return False
        return True

    async def _on_start(self, start: dict) -> bool:
        params = start.get("customParameters") or {}
        session_id = params.get("sid", "")
        token = params.get("tok")
        call_sid = start.get("callSid", "")
        store = self.app_state.session_store

        session = await store.get(session_id)
        if session is None or session.call_sid != call_sid:
            log.warning("media_rejected", reason="unknown_session")
            return False
        if not verify_stream_token(
            self.settings.stream_token_secret.get_secret_value(), token, session_id, call_sid
        ):
            log.warning("media_rejected", reason="bad_token", session_id=session_id)
            return False
        if session.state not in {SessionState.RINGING, SessionState.RECONNECTING}:
            log.warning(
                "media_rejected", reason="bad_state", session_id=session_id, state=session.state
            )
            return False
        live_calls: dict[str, LiveCall] = self.app_state.live_calls
        if session_id in live_calls:
            log.warning("media_rejected", reason="duplicate_stream", session_id=session_id)
            return False

        self.stream_sid = start.get("streamSid")
        fmt_in = start.get("mediaFormat") or {}
        fmt = AudioFormat(
            encoding="mulaw"
            if "mulaw" in str(fmt_in.get("encoding", "audio/x-mulaw"))
            else "pcm16",
            sample_rate=int(fmt_in.get("sampleRate", 8000)),
            channels=int(fmt_in.get("channels", 1)),
        )

        registry = self.app_state.registry
        try:
            t_route = registry.choose("transcriber")
            s_chain = registry.chain("scorer")
            self.transcriber = registry.build("transcriber", t_route)
            scorers = [registry.build("scorer", r) for r in s_chain]
            await self.transcriber.start(fmt)
        except ProviderError as e:
            log.error("media_provider_start_failed", error=str(e), session_id=session_id)
            await store.update(session_id, tier=Tier.UNKNOWN)
            return False

        now = time.time()
        account = await self.app_state.accounts.get(session.account_id)
        self.account = account
        watch_list = account.watch_list if account else []
        policy = CadencePolicy().scaled(self.settings.scoring_speed_factor)
        self.scorer = RollingScorer(
            scorers, on_update=self._publish, policy=policy, watch_list=watch_list
        )
        self.session = await store.update(
            session_id,
            state=SessionState.LIVE,
            stream_sid=self.stream_sid,
            live_at=session.live_at or now,
            provider_choices={"transcriber": t_route.provider, "scorer": s_chain[0].provider},
            funnel={**session.funnel, "start_at": now},
        )
        live_calls[session_id] = self
        self.tasks = [
            asyncio.create_task(self._consume_segments(), name=f"segments-{session_id}"),
            asyncio.create_task(self.scorer.run(), name=f"scorer-{session_id}"),
            asyncio.create_task(self._no_audio_watchdog(), name=f"watchdog-{session_id}"),
            asyncio.create_task(self._stall_watchdog(), name=f"stall-{session_id}"),
        ]
        log.info(
            "media_started",
            session_id=session_id,
            transcriber=t_route.provider,
            scorer=s_chain[0].provider,
        )
        return True

    async def _on_media(self, media: dict) -> None:
        if self.transcriber is None or media.get("track", "inbound") != "inbound":
            return
        payload = media.get("payload")
        if not payload:
            return
        self.frames += 1
        try:
            await self.transcriber.push(base64.b64decode(payload))
        except ProviderError as e:
            log.warning("transcriber_push_failed", error=str(e))

    async def _consume_segments(self) -> None:
        assert self.transcriber is not None and self.scorer is not None
        try:
            async for seg in self.transcriber.segments():
                if seg.is_final:
                    self.last_final_at = time.time()
                    if self.no_audio_flagged:
                        self.no_audio_flagged = False
                        await self._set_tier(self.scorer.dial.tier)
                await self.scorer.on_segment(seg)
        except asyncio.CancelledError:
            return

    async def _no_audio_watchdog(self) -> None:
        timeout = self.app_state.config_service.config.limits.no_audio_timeout_seconds
        timeout *= max(self.settings.scoring_speed_factor, 0.001)
        try:
            await asyncio.sleep(timeout)
            if self.last_final_at is None and self.session is not None:
                self.no_audio_flagged = True
                await self._set_tier(Tier.NO_AUDIO)
                log.info("no_audio", session_id=self.session.id)
                if self.account is not None:
                    await self.app_state.notify.no_audio(self.session, self.account)
        except asyncio.CancelledError:
            return

    async def _stall_watchdog(self) -> None:
        """Transcript arriving but no score for 60 s means a provider hangs. Alerts count it."""
        factor = max(self.settings.scoring_speed_factor, 0.001)
        stall_after = 60.0 * factor
        stalled = False
        try:
            while True:
                await asyncio.sleep(10.0 * factor)
                if self.scorer is None or self.session is None or self.last_final_at is None:
                    continue
                last = self.scorer.last_scored_at or self.scorer.started_at
                now = self.scorer.clock.now()
                if now - last > stall_after and self.scorer.last_final_at > last:
                    if not stalled:
                        stalled = True
                        log.warning(
                            "scoring_stalled", session_id=self.session.id, seconds=now - last
                        )
                else:
                    stalled = False
        except asyncio.CancelledError:
            return

    async def _set_tier(self, tier: Tier) -> None:
        if self.session is None:
            return
        self.session = await self.app_state.session_store.update(self.session.id, tier=tier)

    async def _publish(self, update: ScoreUpdate) -> None:
        if self.session is None:
            return
        store = self.app_state.session_store
        tier = (
            Tier.NO_AUDIO
            if self.no_audio_flagged and update.tier == Tier.LISTENING
            else update.tier
        )
        old_tier = self.session.tier
        self.session = await store.update(
            self.session.id,
            tier=tier,
            dial=update.dial,
            score=update.score if update.score is not None else self.session.score,
            flags=update.flags or self.session.flags,
            reason=update.reason or self.session.reason,
            max_score=update.max_score,
        )
        if tier != old_tier and self.account is not None:
            flags = self.app_state.config_service.flags
            try:
                await self.app_state.notify.tier_changed(
                    self.session,
                    self.account,
                    old_tier,
                    tier,
                    guardian_alerts=flags.guardian_alerts,
                )
            except Exception as e:  # noqa: BLE001 - a push failure must never stop scoring
                log.warning("notify_failed", error=type(e).__name__)
        if update.result is not None:
            await self.app_state.usage_sink.emit(
                UsageEvent(
                    session_id=self.session.id,
                    account_id=self.session.account_id,
                    capability="scorer",
                    provider=update.result.provider,
                    model=update.result.model,
                    usage=update.result.usage,
                    latency_ms=update.result.latency_ms,
                )
            )
        log.info(
            "score",
            session_id=self.session.id,
            tier=tier,
            dial=update.dial,
            score=update.score,
            flags=[f.value for f in update.flags],
            tripwire=update.tripwire,
            provider=update.provider,
        )

    async def finish(self) -> None:
        for t in self.tasks:
            t.cancel()
        if self.scorer is not None:
            self.scorer.stop()
        if self.transcriber is not None and self.session is not None:
            usage = await self.transcriber.close()
            await self.app_state.usage_sink.emit(
                UsageEvent(
                    session_id=self.session.id,
                    account_id=self.session.account_id,
                    capability="transcriber",
                    provider=self.transcriber.name,
                    model=self.transcriber.model,
                    usage=Usage(audio_seconds=usage.audio_seconds),
                )
            )
        if self.session is not None:
            live_calls: dict[str, LiveCall] = self.app_state.live_calls
            live_calls.pop(self.session.id, None)
            funnel = {**self.session.funnel, "stream_closed_at": time.time()}
            await self.app_state.session_store.update(self.session.id, funnel=funnel)
            log.info("media_finished", session_id=self.session.id, frames=self.frames)


@router.websocket("/twilio/media")
async def media_stream(ws: WebSocket) -> None:
    await ws.accept()
    call = LiveCall(ws)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            keep_going = await call.handle(msg)
            if not keep_going:
                break
    except WebSocketDisconnect:
        pass
    finally:
        await call.finish()
        try:
            await ws.close(code=WS_POLICY_VIOLATION if call.session is None else 1000)
        except RuntimeError:
            pass
