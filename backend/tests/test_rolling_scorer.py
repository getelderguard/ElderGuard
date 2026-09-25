from __future__ import annotations

import asyncio

import pytest

from app.providers.base import ProviderUnavailable, ScoreResult, ScoringContext, TranscriptSegment
from app.providers.fake import FakeScorer
from app.scoring.rolling import (
    CadenceDecider,
    CadencePolicy,
    RollingScorer,
    ScoreUpdate,
    ScoringClock,
)
from app.scoring.tiers import Tier


class FakeClock:
    def __init__(self) -> None:
        self.t = 1000.0

    def now(self) -> float:
        return self.t


def seg(text: str, start_s: float, end_s: float) -> TranscriptSegment:
    return TranscriptSegment(
        text=text, is_final=True, t_start_ms=int(start_s * 1000), t_end_ms=int(end_s * 1000)
    )


SCAM_LINES = [
    ("Hello this is Eleanor speaking who is this please?", 0, 3),
    ("Hi Eleanor I'm calling from the Medicare office about your new card", 5, 10),
    ("Before we send it I need to verify your Social Security number right now", 12, 17),
    ("There's a processing fee, buy a gift card at the store and read me the numbers", 19, 25),
    ("And please don't tell anyone about this call until it's done", 27, 31),
]


def test_cadence_first_phase_scores_each_final():
    p = CadencePolicy()
    d = CadenceDecider(p)
    assert not d.should_score(
        now=10,
        started_at=0,
        last_scored_at=None,
        last_final_at=None,
        chars_since_last_score=100,
        tier=Tier.LISTENING,
        forced=False,
        in_flight=False,
    )
    assert d.should_score(
        now=10,
        started_at=0,
        last_scored_at=None,
        last_final_at=9,
        chars_since_last_score=100,
        tier=Tier.LISTENING,
        forced=False,
        in_flight=False,
    )
    # min gap respected even when forced
    assert not d.should_score(
        now=12,
        started_at=0,
        last_scored_at=10,
        last_final_at=11,
        chars_since_last_score=100,
        tier=Tier.LISTENING,
        forced=True,
        in_flight=False,
    )
    # forced ignores debounce and min_new_chars once gap passed
    assert d.should_score(
        now=15,
        started_at=0,
        last_scored_at=10,
        last_final_at=14.9,
        chars_since_last_score=5,
        tier=Tier.LISTENING,
        forced=True,
        in_flight=False,
    )


def test_cadence_slows_when_listening():
    d = CadenceDecider(CadencePolicy())
    kw = dict(
        started_at=0, last_final_at=100, chars_since_last_score=100, forced=False, in_flight=False
    )
    assert not d.should_score(now=110, last_scored_at=105, tier=Tier.LISTENING, **kw)
    assert d.should_score(now=121, last_scored_at=105, tier=Tier.LISTENING, **kw)
    assert d.should_score(now=111, last_scored_at=105, tier=Tier.CAUTION, **kw)
    assert d.should_score(
        now=110,
        last_scored_at=105,
        tier=Tier.LISTENING,
        started_at=0,
        last_final_at=100,
        chars_since_last_score=400,
        forced=False,
        in_flight=False,
    )


async def _drive(scorer: RollingScorer, clock: FakeClock, lines):
    for text, s, e in lines:
        await scorer.on_segment(seg(text, s, e))
        clock.t += 6.0
        if scorer._should_score_now():
            await scorer.score_once()


@pytest.mark.asyncio
async def test_scam_script_reaches_stop():
    clock = FakeClock()
    updates: list[ScoreUpdate] = []

    async def on_update(u: ScoreUpdate) -> None:
        updates.append(u)

    scorer = RollingScorer([FakeScorer()], on_update=on_update, clock=ScoringClock(now=clock.now))
    await _drive(scorer, clock, SCAM_LINES)
    tiers = [u.tier for u in updates]
    assert tiers[0] == Tier.LISTENING  # evidence gate holds the first update
    assert Tier.STOP in tiers
    assert updates[-1].max_score >= 7
    assert any(u.tripwire for u in updates)


@pytest.mark.asyncio
async def test_benign_call_stays_listening():
    clock = FakeClock()
    updates: list[ScoreUpdate] = []

    async def on_update(u: ScoreUpdate) -> None:
        updates.append(u)

    scorer = RollingScorer([FakeScorer()], on_update=on_update, clock=ScoringClock(now=clock.now))
    lines = [
        ("Hi Mom it's me, are you free for lunch on Sunday?", 0, 4),
        ("Oh that would be lovely dear what time were you thinking", 6, 10),
        ("Around noon, I'll pick you up, and bring your reading glasses this time", 12, 17),
        ("I will, thank you for calling sweetheart", 19, 22),
    ]
    await _drive(scorer, clock, lines)
    assert all(u.tier == Tier.LISTENING for u in updates)
    assert updates[-1].dial < 35


@pytest.mark.asyncio
async def test_failure_goes_unknown_then_falls_back():
    clock = FakeClock()
    updates: list[ScoreUpdate] = []

    async def on_update(u: ScoreUpdate) -> None:
        updates.append(u)

    failing = FakeScorer(fail=True)
    healthy = FakeScorer()
    scorer = RollingScorer(
        [failing, healthy], on_update=on_update, clock=ScoringClock(now=clock.now)
    )
    await _drive(scorer, clock, SCAM_LINES[:3])
    assert updates[0].tier == Tier.UNKNOWN
    assert updates[1].tier == Tier.UNKNOWN
    assert scorer.scorer is healthy
    assert updates[2].score is not None


@pytest.mark.asyncio
async def test_unknown_never_reports_safe_score():
    class Flaky:
        name = "flaky"
        model = "m"

        async def score(self, ctx: ScoringContext, timeout_s: float) -> ScoreResult:
            raise ProviderUnavailable("down")

    clock = FakeClock()
    updates: list[ScoreUpdate] = []

    async def on_update(u: ScoreUpdate) -> None:
        updates.append(u)

    scorer = RollingScorer([Flaky()], on_update=on_update, clock=ScoringClock(now=clock.now))
    await _drive(scorer, clock, SCAM_LINES[:2])
    assert all(u.tier == Tier.UNKNOWN and u.score is None for u in updates)


@pytest.mark.asyncio
async def test_run_loop_scores_on_wall_clock():
    updates: list[ScoreUpdate] = []

    async def on_update(u: ScoreUpdate) -> None:
        updates.append(u)

    policy = CadencePolicy().scaled(0.02)
    scorer = RollingScorer([FakeScorer()], on_update=on_update, policy=policy)
    task = asyncio.create_task(scorer.run())
    await scorer.on_segment(seg(SCAM_LINES[0][0], 0, 3))
    await asyncio.sleep(0.3)
    scorer.stop()
    task.cancel()
    assert len(updates) >= 1
