"""Deepgram streaming transcription. Takes 8 kHz mulaw straight from Twilio, no stream cap."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlencode

import structlog
import websockets
from websockets.asyncio.client import ClientConnection, connect

from app.providers.base import (
    AudioFormat,
    ProviderUnavailable,
    TranscriberUsage,
    TranscriptSegment,
)

log = structlog.get_logger("deepgram")

DEEPGRAM_URL = "wss://api.deepgram.com/v1/listen"
KEEPALIVE_SECONDS = 5.0


class DeepgramTranscriber:
    name = "deepgram"

    def __init__(
        self, api_key: str, model: str = "nova-3", params: dict[str, Any] | None = None
    ) -> None:
        self.model = model
        self._api_key = api_key
        self._params = dict(params or {})
        self._ws: ClientConnection | None = None
        self._queue: asyncio.Queue[TranscriptSegment | None] = asyncio.Queue()
        self._tasks: list[asyncio.Task[None]] = []
        self._bytes = 0
        self._fmt = AudioFormat()
        self._closed = False

    async def start(self, fmt: AudioFormat) -> None:
        self._fmt = fmt
        query = {
            "model": self.model,
            "encoding": "mulaw" if fmt.encoding == "mulaw" else "linear16",
            "sample_rate": fmt.sample_rate,
            "channels": fmt.channels,
            "interim_results": "true",
            "punctuate": "true",
            "smart_format": "true",
            "endpointing": self._params.get("endpointing", 300),
            "language": self._params.get("language", "en-US"),
        }
        url = f"{DEEPGRAM_URL}?{urlencode(query)}"
        try:
            self._ws = await connect(
                url, additional_headers={"Authorization": f"Token {self._api_key}"}
            )
        except (OSError, websockets.exceptions.WebSocketException) as e:
            raise ProviderUnavailable(f"deepgram connect failed: {e}") from e
        self._tasks = [
            asyncio.create_task(self._reader(), name="deepgram-reader"),
            asyncio.create_task(self._keepalive(), name="deepgram-keepalive"),
        ]

    async def push(self, audio: bytes) -> None:
        if self._ws is None or self._closed:
            return
        self._bytes += len(audio)
        try:
            await self._ws.send(audio)
        except websockets.exceptions.ConnectionClosed as e:
            raise ProviderUnavailable(f"deepgram stream closed: {e}") from e

    async def segments(self) -> AsyncIterator[TranscriptSegment]:
        while True:
            seg = await self._queue.get()
            if seg is None:
                return
            yield seg

    async def close(self) -> TranscriberUsage:
        if self._closed:
            return self._usage()
        self._closed = True
        if self._ws is not None:
            try:
                await self._ws.send(json.dumps({"type": "CloseStream"}))
                await asyncio.wait_for(self._ws.close(), timeout=2.0)
            except Exception:  # noqa: BLE001 - best effort shutdown
                pass
        for t in self._tasks:
            t.cancel()
        await self._queue.put(None)
        return self._usage()

    def _usage(self) -> TranscriberUsage:
        bytes_per_sec = self._fmt.sample_rate * (1 if self._fmt.encoding == "mulaw" else 2)
        return TranscriberUsage(audio_seconds=self._bytes / bytes_per_sec)

    async def _keepalive(self) -> None:
        try:
            while self._ws is not None and not self._closed:
                await asyncio.sleep(KEEPALIVE_SECONDS)
                await self._ws.send(json.dumps({"type": "KeepAlive"}))
        except (asyncio.CancelledError, websockets.exceptions.ConnectionClosed):
            return

    async def _reader(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if msg.get("type") != "Results":
                    continue
                alts = (msg.get("channel") or {}).get("alternatives") or []
                if not alts:
                    continue
                text = (alts[0].get("transcript") or "").strip()
                if not text:
                    continue
                start = float(msg.get("start", 0.0))
                duration = float(msg.get("duration", 0.0))
                await self._queue.put(
                    TranscriptSegment(
                        text=text,
                        is_final=bool(msg.get("is_final")),
                        t_start_ms=int(start * 1000),
                        t_end_ms=int((start + duration) * 1000),
                    )
                )
        except asyncio.CancelledError:
            return
        except websockets.exceptions.ConnectionClosed as e:
            log.warning("deepgram_closed", code=e.code)
        finally:
            await self._queue.put(None)
