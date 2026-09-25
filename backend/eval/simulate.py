"""Pipeline simulator: text -> synthesized speech -> mulaw 8 kHz -> streaming STT -> scorer.

    cd backend && uv run python eval/simulate.py --limit 5                 # fakes end to end
    cd backend && STT_API_KEY=... uv run python eval/simulate.py --transcriber deepgram --limit 3

With the fake synthesizer and transcriber the audio is silence and the transcript is the
fixture text, so this only proves the plumbing. With a real transcriber the scorer sees
what STT actually heard, including its mistakes, which is the point of the exercise. A real
voice synthesizer lands with the takeover work in M3; until then `--synth` only has `fake`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from array import array
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.providers.base import (  # noqa: E402
    AudioFormat,
    StreamingTranscriber,
    TranscriptSegment,
    VoiceSynthesizer,  # noqa: E402
)
from app.providers.fake import FakeSynthesizer, FakeTranscriber  # noqa: E402
from app.scoring.rolling import CadencePolicy  # noqa: E402
from app.telephony.codec import pcm16_to_mulaw  # noqa: E402

from eval.run import (  # noqa: E402
    FixtureResult,
    load_fixtures,
    make_scorer,
    print_table,
    replay,
    summarize,
)

FRAME_BYTES = 160  # 20 ms of mulaw at 8 kHz, what Twilio sends


def downsample_2x(pcm16: bytes) -> bytes:
    """16 kHz -> 8 kHz by averaging sample pairs. Good enough for a telephone band."""
    samples = array("h")
    samples.frombytes(pcm16)
    out = array("h", ((samples[i] + samples[i + 1]) // 2 for i in range(0, len(samples) - 1, 2)))
    return out.tobytes()


def to_mulaw_8k(audio: bytes, fmt: str) -> bytes:
    if fmt == "ulaw_8000":
        return audio
    if fmt == "pcm_16000":
        return pcm16_to_mulaw(downsample_2x(audio))
    if fmt == "pcm_8000":
        return pcm16_to_mulaw(audio)
    raise ValueError(f"unsupported synth format {fmt}")


def make_synth(kind: str) -> tuple[VoiceSynthesizer, str]:
    if kind == "fake":
        return FakeSynthesizer(), "ulaw_8000"
    sys.exit(f"unknown synthesizer {kind}")


def make_transcriber(kind: str) -> StreamingTranscriber:
    if kind == "fake":
        return FakeTranscriber(script=[])
    if kind == "deepgram":
        key = os.environ.get("STT_API_KEY")
        if not key:
            sys.exit("STT_API_KEY is not set; refusing to run the real transcriber")
        from app.providers.deepgram_transcriber import DeepgramTranscriber

        return DeepgramTranscriber(api_key=key)
    sys.exit(f"unknown transcriber {kind}")


async def transcribe_fixture(
    fixture: dict, synth_kind: str, transcriber_kind: str, realtime: bool
) -> list[dict]:
    """Returns segments in the fixture shape, but with the transcriber's text and timing."""
    synth, synth_fmt = make_synth(synth_kind)
    transcriber = make_transcriber(transcriber_kind)
    await transcriber.start(AudioFormat())
    heard: list[TranscriptSegment] = []

    async def collect() -> None:
        async for seg in transcriber.segments():
            if seg.is_final:
                heard.append(seg)

    reader = asyncio.create_task(collect())
    audio_ms = 0
    for seg in fixture["segments"]:
        # Silence up to the segment's start so timestamps stay honest.
        gap_ms = max(0, int(seg["t"] * 1000) - audio_ms)
        audio_ms += await push(transcriber, bytes([0xFF]) * (gap_ms * 8), realtime)
        clip = to_mulaw_8k(await synth.synthesize(seg["text"], voice_ref="eval"), synth_fmt)
        start_ms = audio_ms
        audio_ms += await push(transcriber, clip, realtime)
        if transcriber_kind == "fake":
            await transcriber.feed_text(seg["text"], start_ms, audio_ms)  # type: ignore[attr-defined]
    await transcriber.close()
    await reader
    return [{"t": s.t_start_ms / 1000.0, "speaker": "unknown", "text": s.text} for s in heard]


async def push(transcriber: StreamingTranscriber, audio: bytes, realtime: bool) -> int:
    for i in range(0, len(audio), FRAME_BYTES):
        await transcriber.push(audio[i : i + FRAME_BYTES])
        if realtime:
            await asyncio.sleep(0.02)
    return len(audio) // 8  # ms of audio at 8 kHz mulaw


async def main_async(args: argparse.Namespace) -> None:
    fixtures = load_fixtures(args.limit, args.seed)
    policy = CadencePolicy()
    results: list[FixtureResult] = []
    for fx in fixtures:
        heard = await transcribe_fixture(fx, args.synth, args.transcriber, args.realtime)
        if not heard:
            print(f"  {fx['id']}: transcriber returned nothing")
            continue
        simulated = {**fx, "segments": heard}
        r = await replay(simulated, make_scorer(args.scorer, args.model), policy)
        results.append(r)
        print(
            f"  {fx['id']:<45} heard {len(heard):>3} segs  "
            f"max_tier={r.max_tier:<9} t_stop={r.t_stop}"
        )
    if results:
        summary = summarize(results)
        print_table(summary, f"{args.scorer} via {args.transcriber}")
        out = Path(__file__).resolve().parent / "out" / "simulate.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(
            json.dumps({"summary": summary, "results": [r.__dict__ for r in results]}, indent=1)
        )
        print(f"\nreport: {out}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--synth", choices=["fake"], default="fake")
    ap.add_argument("--transcriber", choices=["fake", "deepgram"], default="fake")
    ap.add_argument("--scorer", choices=["fake", "anthropic"], default="fake")
    ap.add_argument("--model", default=None)
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument(
        "--realtime", action="store_true", help="pace audio at 1x (needed for some STT)"
    )
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()
