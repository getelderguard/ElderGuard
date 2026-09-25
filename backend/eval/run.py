"""Offline evaluation of the rolling scorer over the fixture corpus.

    cd backend && uv run python eval/run.py                  # fake scorer, whole corpus
    cd backend && uv run python eval/run.py --gate           # exit 1 if a gate fails
    cd backend && ANTHROPIC_API_KEY=... uv run python eval/run.py --scorer anthropic --limit 40

Each transcript is replayed against RollingScorer with a fake clock at the real cadence
constants, so the numbers reflect the hysteresis, the evidence gate, the trip-wire and the
adaptive cadence exactly as production runs them. Scorer latency is not simulated: virtual
time only advances with the transcript.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.providers.base import ScamScorer, TranscriptSegment  # noqa: E402
from app.providers.metrics import estimate_cost  # noqa: E402
from app.scoring.rolling import (  # noqa: E402
    CadencePolicy,
    RollingScorer,
    ScoreUpdate,
    ScoringClock,
)
from app.scoring.tiers import Tier  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent / "out"
WORDS_PER_S = 2.4
TAIL_S = 20.0  # virtual seconds to keep ticking after the last segment

TIER_RANK = {Tier.LISTENING: 0, Tier.NO_AUDIO: 0, Tier.UNKNOWN: 0, Tier.CAUTION: 1, Tier.STOP: 2}

# Gates. Fake-scorer numbers only prove the harness and hysteresis behave; the model is not
# under test. Anthropic numbers are the plan's launch gates.
GATES = {
    "fake": {"stop_fp_max": 0.01, "caution_fp_max": 0.15, "stop_recall_min": 0.80},
    "anthropic": {"stop_fp_max": 0.01, "caution_fp_max": 0.15, "median_tts_action_max_s": 60.0},
}


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def now(self) -> float:
        return self.t


@dataclass
class FixtureResult:
    id: str
    label: str
    category: str
    duration_s: float
    first_action_t: float | None
    final_tier: str = "listening"
    max_tier: str = "listening"
    t_caution: float | None = None
    t_stop: float | None = None
    scorer_calls: int = 0
    cost_usd: float = 0.0
    skipped: bool = False
    timeline: list[dict] = field(default_factory=list)


def load_fixtures(limit: int | None, seed: int) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(FIXTURES.glob("*.jsonl")):
        with path.open() as f:
            rows.extend(json.loads(line) for line in f if line.strip())
    random.Random(seed).shuffle(rows)
    return rows[:limit] if limit else rows


def make_scorer(kind: str, model: str | None) -> ScamScorer:
    if kind == "fake":
        from app.providers.fake import FakeScorer

        return FakeScorer()
    if kind == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            sys.exit("ANTHROPIC_API_KEY is not set; refusing to run the real scorer")
        from app.providers.anthropic_scorer import AnthropicScorer

        return AnthropicScorer(api_key=key, model=model or "claude-sonnet-5")
    sys.exit(f"unknown scorer {kind}")


async def replay(fixture: dict, scorer: ScamScorer, policy: CadencePolicy) -> FixtureResult:
    clock = FakeClock()
    res = FixtureResult(
        id=fixture["id"],
        label=fixture["label"],
        category=fixture["category"],
        duration_s=fixture["segments"][-1]["t"],
        first_action_t=fixture.get("first_action_t"),
    )

    async def on_update(u: ScoreUpdate) -> None:
        t = clock.t
        res.timeline.append(
            {"t": round(t, 1), "tier": u.tier.value, "score": u.score, "dial": u.dial}
        )
        if u.result is not None:
            res.cost_usd += estimate_cost(u.result.provider, u.result.model, u.result.usage)
        if u.tier == Tier.CAUTION and res.t_caution is None:
            res.t_caution = round(t, 1)
        if u.tier == Tier.STOP and res.t_stop is None:
            res.t_stop = round(t, 1)
        if TIER_RANK[u.tier] > TIER_RANK[Tier(res.max_tier)]:
            res.max_tier = u.tier.value
        res.final_tier = u.tier.value

    rs = RollingScorer([scorer], on_update=on_update, policy=policy, clock=ScoringClock(clock.now))

    async def tick_until(t_end: float) -> None:
        while clock.t < t_end:
            clock.t = min(t_end, clock.t + policy.loop_tick_s)
            if rs._should_score_now():
                await rs.score_once()

    for seg in fixture["segments"]:
        await tick_until(seg["t"])
        words = max(1, len(seg["text"].split()))
        await rs.on_segment(
            TranscriptSegment(
                text=seg["text"],
                is_final=True,
                t_start_ms=int(seg["t"] * 1000),
                t_end_ms=int((seg["t"] + words / WORDS_PER_S) * 1000),
            )
        )
    await tick_until(res.duration_s + TAIL_S)
    res.scorer_calls = rs.scores_run
    return res


def summarize(results: list[FixtureResult]) -> dict:
    done = [r for r in results if not r.skipped]
    benign = [r for r in done if r.label == "benign"]
    scam = [r for r in done if r.label == "scam"]
    stops = [r for r in scam if r.t_stop is not None]
    tts_start = [r.t_stop for r in stops]
    tts_action = [
        max(0.0, r.t_stop - r.first_action_t) for r in stops if r.first_action_t is not None
    ]
    minutes = sum(r.duration_s for r in done) / 60.0 or 1.0
    per_cat: dict[str, dict] = {}
    for r in done:
        c = per_cat.setdefault(r.category, {"label": r.label, "n": 0, "caution": 0, "stop": 0})
        c["n"] += 1
        c["caution"] += r.max_tier in {"caution", "stop"}
        c["stop"] += r.max_tier == "stop"

    def pct(n: int, d: int) -> float:
        return round(n / d, 4) if d else 0.0

    return {
        "n_benign": len(benign),
        "n_scam": len(scam),
        "n_skipped": len(results) - len(done),
        "stop_fp": pct(sum(r.max_tier == "stop" for r in benign), len(benign)),
        "caution_fp": pct(sum(r.max_tier in {"caution", "stop"} for r in benign), len(benign)),
        "stop_recall": pct(len(stops), len(scam)),
        "caution_recall": pct(sum(r.max_tier in {"caution", "stop"} for r in scam), len(scam)),
        "median_tts_from_start_s": round(statistics.median(tts_start), 1) if tts_start else None,
        "p90_tts_from_start_s": round(_p90(tts_start), 1) if tts_start else None,
        "median_tts_action_s": round(statistics.median(tts_action), 1) if tts_action else None,
        "p90_tts_action_s": round(_p90(tts_action), 1) if tts_action else None,
        "scorer_calls_per_audio_minute": round(sum(r.scorer_calls for r in done) / minutes, 2),
        "cost_per_6min_call_usd": round(sum(r.cost_usd for r in done) / minutes * 6, 4),
        "per_category": per_cat,
    }


def _p90(xs: list[float]) -> float:
    s = sorted(xs)
    return s[min(len(s) - 1, int(round(0.9 * (len(s) - 1))))]


def check_gates(summary: dict, kind: str) -> list[str]:
    g = GATES[kind]
    failures: list[str] = []
    if summary["stop_fp"] > g["stop_fp_max"]:
        failures.append(f"STOP false positives {summary['stop_fp']:.1%} > {g['stop_fp_max']:.0%}")
    if summary["caution_fp"] > g["caution_fp_max"]:
        failures.append(
            f"CAUTION false positives {summary['caution_fp']:.1%} > {g['caution_fp_max']:.0%}"
        )
    if "stop_recall_min" in g and summary["stop_recall"] < g["stop_recall_min"]:
        failures.append(f"STOP recall {summary['stop_recall']:.1%} < {g['stop_recall_min']:.0%}")
    if "median_tts_action_max_s" in g:
        m = summary["median_tts_action_s"]
        if m is None or m > g["median_tts_action_max_s"]:
            failures.append(
                f"median time-to-STOP after first ask {m} s > {g['median_tts_action_max_s']} s"
            )
    return failures


def print_table(summary: dict, kind: str) -> None:
    rows = [
        ("benign / scam transcripts", f"{summary['n_benign']} / {summary['n_scam']}"),
        ("STOP false-positive rate (benign)", f"{summary['stop_fp']:.1%}"),
        ("CAUTION false-positive rate (benign)", f"{summary['caution_fp']:.1%}"),
        ("STOP recall (scam)", f"{summary['stop_recall']:.1%}"),
        ("CAUTION-or-worse recall (scam)", f"{summary['caution_recall']:.1%}"),
        (
            "time-to-STOP from call start, median / p90",
            f"{summary['median_tts_from_start_s']} / {summary['p90_tts_from_start_s']} s",
        ),
        (
            "time-to-STOP after first ask, median / p90",
            f"{summary['median_tts_action_s']} / {summary['p90_tts_action_s']} s",
        ),
        ("scorer calls per audio minute", f"{summary['scorer_calls_per_audio_minute']}"),
        ("estimated cost per 6-minute call", f"${summary['cost_per_6min_call_usd']:.4f}"),
    ]
    width = max(len(r[0]) for r in rows)
    print(f"\nscorer = {kind}")
    for k, v in rows:
        print(f"  {k:<{width}}  {v}")
    cats = summary["per_category"]
    weak = {c: v for c, v in cats.items() if v["label"] == "scam" and v["stop"] / v["n"] < 0.8}
    fps = {c: v for c, v in cats.items() if v["label"] == "benign" and v["caution"]}
    if weak:
        print("  scam categories under 80% STOP:")
        for c, v in sorted(weak.items()):
            print(f"    {c:<40} stop {v['stop']}/{v['n']}  caution {v['caution']}/{v['n']}")
    if fps:
        print("  benign categories that reached CAUTION or STOP:")
        for c, v in sorted(fps.items()):
            print(f"    {c:<40} caution {v['caution']}/{v['n']}  stop {v['stop']}/{v['n']}")


async def run_once(args: argparse.Namespace, seed: int) -> tuple[dict, list[FixtureResult]]:
    fixtures = load_fixtures(args.limit, seed)
    policy = CadencePolicy()
    sem = asyncio.Semaphore(4 if args.scorer == "anthropic" else 32)
    spent = 0.0
    results: list[FixtureResult] = []

    async def one(fx: dict) -> FixtureResult:
        nonlocal spent
        async with sem:
            if args.scorer == "anthropic" and spent >= args.max_cost_usd:
                r = FixtureResult(
                    fx["id"],
                    fx["label"],
                    fx["category"],
                    fx["segments"][-1]["t"],
                    fx.get("first_action_t"),
                )
                r.skipped = True
                return r
            r = await replay(fx, make_scorer(args.scorer, args.model), policy)
            spent += r.cost_usd
            return r

    results = list(await asyncio.gather(*(one(fx) for fx in fixtures)))
    skipped = sum(r.skipped for r in results)
    if skipped:
        print(f"  cost cap ${args.max_cost_usd:.2f} reached; {skipped} transcripts skipped")
    return summarize(results), results


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--scorer", choices=["fake", "anthropic"], default="fake")
    ap.add_argument("--model", default=None, help="model id for the real scorer")
    ap.add_argument("--limit", type=int, default=None, help="evaluate a random subset")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--runs", type=int, default=1, help="repeat with seed+k and report variance")
    ap.add_argument("--max-cost-usd", type=float, default=2.00)
    ap.add_argument("--gate", action="store_true", help="exit non-zero when a gate fails")
    args = ap.parse_args()
    if args.scorer == "anthropic" and not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set; refusing to run the real scorer")

    t0 = time.time()
    summaries: list[dict] = []
    last_results: list[FixtureResult] = []
    for k in range(args.runs):
        summary, last_results = asyncio.run(run_once(args, args.seed + k))
        summaries.append(summary)
        print_table(summary, args.scorer)

    if args.runs > 1:
        print("\nvariance across runs (mean ± stdev):")
        for key in ("stop_fp", "caution_fp", "stop_recall", "median_tts_action_s"):
            xs = [s[key] for s in summaries if s[key] is not None]
            if len(xs) >= 2:
                print(f"  {key:<24} {statistics.mean(xs):.3f} ± {statistics.stdev(xs):.3f}")

    OUT.mkdir(exist_ok=True)
    report = {
        "scorer": args.scorer,
        "model": args.model,
        "runs": summaries,
        "results": [asdict(r) for r in last_results],
        "elapsed_s": round(time.time() - t0, 1),
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=1))
    print(f"\nreport: {OUT / 'report.json'}  ({report['elapsed_s']} s)")

    if args.gate:
        failures = check_gates(summaries[-1], args.scorer)
        if failures:
            print("\nGATE FAILED")
            for f in failures:
                print(f"  - {f}")
            sys.exit(1)
        print("\nGATE PASSED")


if __name__ == "__main__":
    main()
