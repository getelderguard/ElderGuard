"""Rolling transcript, adaptive cadence, dial with hysteresis, and the async scoring loop."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

import structlog

from app.providers.base import (
    ACTION_FLAGS,
    ProviderError,
    RedFlag,
    ScamScorer,
    ScoreResult,
    ScoringContext,
    TranscriptSegment,
)
from app.scoring.tiers import Tier
from app.scoring.tripwire import tripwire_hits

log = structlog.get_logger("scoring")


@dataclass
class Segment:
    text: str
    t_start_ms: int
    t_end_ms: int


class RollingTranscript:
    def __init__(
        self, window_s: float = 90.0, max_chars: int = 1500, max_partial_chars: int = 200
    ) -> None:
        self.window_s = window_s
        self.max_chars = max_chars
        self.max_partial_chars = max_partial_chars
        self.finals: list[Segment] = []
        self.partial: str = ""
        self._chars_total = 0

    def add(self, seg: TranscriptSegment) -> None:
        if seg.is_final:
            self.finals.append(Segment(seg.text, seg.t_start_ms, seg.t_end_ms))
            self._chars_total += len(seg.text) + 1
            self.partial = ""
        else:
            self.partial = seg.text[-self.max_partial_chars :]

    @property
    def total_chars(self) -> int:
        return self._chars_total

    @property
    def last_end_ms(self) -> int:
        return self.finals[-1].t_end_ms if self.finals else 0

    @property
    def word_count(self) -> int:
        return sum(len(s.text.split()) for s in self.finals)

    @property
    def duration_s(self) -> float:
        if not self.finals:
            return 0.0
        return (self.finals[-1].t_end_ms - self.finals[0].t_start_ms) / 1000.0

    @property
    def looks_two_party(self) -> bool:
        """Cheap heuristic: a question was asked, or there was a real pause between segments."""
        if any("?" in s.text for s in self.finals):
            return True
        for prev, nxt in zip(self.finals, self.finals[1:], strict=False):
            if nxt.t_start_ms - prev.t_end_ms >= 800:
                return True
        return False

    def window_text(self) -> str:
        if not self.finals:
            return ""
        cutoff = self.last_end_ms - int(self.window_s * 1000)
        text = " ".join(s.text for s in self.finals if s.t_end_ms >= cutoff)
        return text[-self.max_chars :]

    def full_text(self) -> str:
        return " ".join(s.text for s in self.finals)


@dataclass(frozen=True)
class CadencePolicy:
    first_phase_s: float = 60.0
    listening_interval_s: float = 15.0
    caution_interval_s: float = 5.0
    stop_interval_s: float = 8.0
    min_gap_s: float = 4.0
    debounce_s: float = 0.8
    min_new_chars: int = 40
    listening_new_chars: int = 300
    score_timeout_s: float = 6.0
    loop_tick_s: float = 0.25

    def scaled(self, factor: float) -> CadencePolicy:
        if factor == 1.0:
            return self
        f = max(factor, 0.001)
        return CadencePolicy(
            first_phase_s=self.first_phase_s * f,
            listening_interval_s=self.listening_interval_s * f,
            caution_interval_s=self.caution_interval_s * f,
            stop_interval_s=self.stop_interval_s * f,
            min_gap_s=self.min_gap_s * f,
            debounce_s=self.debounce_s * f,
            min_new_chars=self.min_new_chars,
            listening_new_chars=self.listening_new_chars,
            score_timeout_s=self.score_timeout_s,
            loop_tick_s=max(0.01, self.loop_tick_s * f),
        )


@dataclass
class DialThresholds:
    caution_on: float = 35.0
    caution_off: float = 25.0
    stop_on: float = 70.0
    rise_alpha: float = 0.6
    fall_alpha: float = 0.25


@dataclass
class DialState:
    thresholds: DialThresholds = field(default_factory=DialThresholds)
    dial: float = 0.0
    tier: Tier = Tier.LISTENING
    max_score: int = 0
    flags_union: set[RedFlag] = field(default_factory=set)
    recent: deque[ScoreResult] = field(default_factory=lambda: deque(maxlen=2))
    consecutive_failures: int = 0
    rescore_now: bool = False
    _tier_before_unknown: Tier | None = None

    def apply(self, result: ScoreResult, evidence_ready: bool) -> Tier:
        self.consecutive_failures = 0
        self.rescore_now = False
        if self.tier == Tier.UNKNOWN and self._tier_before_unknown is not None:
            self.tier = self._tier_before_unknown
            self._tier_before_unknown = None
        target = result.score * 10.0
        alpha = self.thresholds.rise_alpha if target > self.dial else self.thresholds.fall_alpha
        self.dial = self.dial + alpha * (target - self.dial)
        self.max_score = max(self.max_score, result.score)
        self.flags_union.update(result.red_flags)
        self.recent.append(result)

        if not evidence_ready:
            self.tier = Tier.LISTENING
            return self.tier

        t = self.thresholds
        if self.tier == Tier.STOP:
            if self._last_n_scores_at_most(2, 5):
                self.tier = Tier.CAUTION
            return self.tier
        if self.tier == Tier.LISTENING and self.dial >= t.caution_on:
            self.tier = Tier.CAUTION
        # A high score straight from LISTENING passes through CAUTION in the same step,
        # so STOP still requires two consecutive high scores with an action flag.
        if self.tier == Tier.CAUTION:
            if self._two_signal_stop():
                self.tier = Tier.STOP
            elif result.score >= 9:
                self.rescore_now = True
            elif self.dial <= t.caution_off and self._last_n_scores_at_most(2, 3):
                self.tier = Tier.LISTENING
        return self.tier

    def apply_failure(self) -> Tier:
        self.consecutive_failures += 1
        if self.tier != Tier.UNKNOWN:
            self._tier_before_unknown = self.tier
            self.tier = Tier.UNKNOWN
        return self.tier

    def _two_signal_stop(self) -> bool:
        if len(self.recent) < 2:
            return False
        if not all(r.score >= 7 for r in self.recent):
            return False
        cats: set[RedFlag] = set()
        for r in self.recent:
            cats.update(r.red_flags)
        return len(cats) >= 2 and any(f in ACTION_FLAGS for f in cats)

    def _last_n_scores_at_most(self, n: int, ceiling: int) -> bool:
        if len(self.recent) < n:
            return False
        return all(r.score <= ceiling for r in list(self.recent)[-n:])


@dataclass
class ScoringClock:
    now: Callable[[], float] = time.monotonic


class CadenceDecider:
    """Pure decision: given state and timing, should we score now?"""

    def __init__(self, policy: CadencePolicy) -> None:
        self.policy = policy

    def should_score(
        self,
        *,
        now: float,
        started_at: float,
        last_scored_at: float | None,
        last_final_at: float | None,
        chars_since_last_score: int,
        tier: Tier,
        forced: bool,
        in_flight: bool,
    ) -> bool:
        p = self.policy
        if in_flight or last_final_at is None:
            return False
        if last_scored_at is not None and now - last_scored_at < p.min_gap_s:
            return False
        if forced:
            return True
        if chars_since_last_score < p.min_new_chars:
            return False
        if now - last_final_at < p.debounce_s:
            return False
        if last_scored_at is None:
            return True
        elapsed = now - started_at
        if elapsed < p.first_phase_s:
            return True
        since = now - last_scored_at
        if tier == Tier.STOP:
            return since >= p.stop_interval_s
        if tier == Tier.CAUTION or tier == Tier.UNKNOWN:
            return since >= p.caution_interval_s
        return since >= p.listening_interval_s or chars_since_last_score >= p.listening_new_chars


@dataclass
class ScoreUpdate:
    tier: Tier
    dial: float
    score: int | None
    flags: list[RedFlag]
    reason: str
    max_score: int
    provider: str | None
    model: str | None
    result: ScoreResult | None
    tripwire: list[str]


OnUpdate = Callable[[ScoreUpdate], Awaitable[None]]


class RollingScorer:
    """Consumes transcript segments and drives scoring; publishes updates through a callback."""

    def __init__(
        self,
        scorers: list[ScamScorer],
        *,
        on_update: OnUpdate,
        policy: CadencePolicy = CadencePolicy(),
        evidence_gate=None,
        watch_list: list[str] | None = None,
        clock: ScoringClock | None = None,
        transcript: RollingTranscript | None = None,
        dial: DialState | None = None,
    ) -> None:
        from app.scoring.evidence import EvidenceGate

        if not scorers:
            raise ValueError("at least one scorer is required")
        self.scorers = list(scorers)
        self._scorer_index = 0
        self.on_update = on_update
        self.policy = policy
        self.decider = CadenceDecider(policy)
        self.gate = evidence_gate or EvidenceGate()
        self.watch_list = list(watch_list or [])
        self.clock = clock or ScoringClock()
        self.transcript = transcript or RollingTranscript()
        self.dial = dial or DialState()
        self.started_at = self.clock.now()
        self.last_scored_at: float | None = None
        self.last_final_at: float | None = None
        self.chars_at_last_score = 0
        self.forced = False
        self.forced_hits: list[str] = []
        self.in_flight = False
        self.dirty = False
        self.scores_run = 0
        self._stop = asyncio.Event()

    @property
    def scorer(self) -> ScamScorer:
        return self.scorers[self._scorer_index]

    async def on_segment(self, seg: TranscriptSegment) -> None:
        self.transcript.add(seg)
        if seg.is_final:
            self.last_final_at = self.clock.now()
            hits = tripwire_hits(seg.text)
            if hits:
                self.forced = True
                self.forced_hits = hits

    async def run(self) -> None:
        try:
            while not self._stop.is_set():
                if self._should_score_now():
                    await self.score_once()
                    if self.dirty and not self._stop.is_set():
                        self.dirty = False
                        await self.score_once()
                await asyncio.sleep(self.policy.loop_tick_s)
        except asyncio.CancelledError:
            return

    def stop(self) -> None:
        self._stop.set()

    def _should_score_now(self) -> bool:
        return self.decider.should_score(
            now=self.clock.now(),
            started_at=self.started_at,
            last_scored_at=self.last_scored_at,
            last_final_at=self.last_final_at,
            chars_since_last_score=self.transcript.total_chars - self.chars_at_last_score,
            tier=self.dial.tier,
            forced=self.forced or self.dial.rescore_now,
            in_flight=self.in_flight,
        )

    async def score_once(self) -> ScoreUpdate:
        self.in_flight = True
        hits, self.forced_hits, self.forced = self.forced_hits, [], False
        now = self.clock.now()
        ctx = ScoringContext(
            window_text=self.transcript.window_text(),
            partial_text=self.transcript.partial,
            prior_flags=sorted(self.dial.flags_union, key=lambda f: f.value),
            elapsed_s=now - self.started_at,
            watch_list=self.watch_list,
        )
        self.chars_at_last_score = self.transcript.total_chars
        evidence_ready = self.gate.ready(self.transcript)
        try:
            result = await self.scorer.score(ctx, timeout_s=self.policy.score_timeout_s)
            tier = self.dial.apply(result, evidence_ready)
            update = ScoreUpdate(
                tier=tier,
                dial=round(self.dial.dial, 1),
                score=result.score,
                flags=list(result.red_flags),
                reason=result.reasoning,
                max_score=self.dial.max_score,
                provider=result.provider,
                model=result.model,
                result=result,
                tripwire=hits,
            )
        except ProviderError as e:
            tier = self.dial.apply_failure()
            log.warning(
                "scorer_failed",
                provider=self.scorer.name,
                error=str(e),
                failures=self.dial.consecutive_failures,
            )
            if self.dial.consecutive_failures >= 2 and self._scorer_index + 1 < len(self.scorers):
                self._scorer_index += 1
                self.dial.consecutive_failures = 0
                log.warning("scorer_fallback", provider=self.scorer.name)
            update = ScoreUpdate(
                tier=tier,
                dial=round(self.dial.dial, 1),
                score=None,
                flags=[],
                reason="",
                max_score=self.dial.max_score,
                provider=self.scorer.name,
                model=self.scorer.model,
                result=None,
                tripwire=hits,
            )
        finally:
            self.last_scored_at = self.clock.now()
            self.scores_run += 1
            self.in_flight = False
        await self.on_update(update)
        return update
