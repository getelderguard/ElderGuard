from app.providers.base import RedFlag, ScoreResult
from app.scoring.rolling import DialState
from app.scoring.tiers import Tier


def r(score: int, *flags: RedFlag) -> ScoreResult:
    return ScoreResult(
        score=score, reasoning="t", red_flags=list(flags), provider="fake", model="fake"
    )


def test_no_tier_change_without_evidence():
    d = DialState()
    assert (
        d.apply(r(10, RedFlag.UNUSUAL_PAYMENT, RedFlag.URGENCY), evidence_ready=False)
        == Tier.LISTENING
    )
    assert d.dial > 0


def test_listening_to_caution_on_dial():
    d = DialState()
    assert d.apply(r(5), True) == Tier.LISTENING  # 0 + 0.6*50 = 30, below 35
    assert d.apply(r(5), True) == Tier.CAUTION  # 30 + 0.6*20 = 42
    # Falling back needs the dial under 25 and two consecutive low scores.
    assert d.apply(r(2), True) == Tier.CAUTION
    assert d.apply(r(1), True) == Tier.CAUTION  # dial 42 -> 36.5 -> 29.9, still above 25
    assert d.apply(r(1), True) == Tier.LISTENING  # 29.9 -> 24.9


def test_stop_needs_two_signals_with_action_flag():
    d = DialState()
    d.apply(r(8, RedFlag.GOVERNMENT_IMPERSONATION, RedFlag.URGENCY), True)
    tier = d.apply(r(8, RedFlag.GOVERNMENT_IMPERSONATION, RedFlag.URGENCY), True)
    assert tier == Tier.CAUTION  # no action flag
    tier = d.apply(r(8, RedFlag.UNUSUAL_PAYMENT), True)
    assert tier == Tier.STOP  # union over last two: GOV/URGENCY + UNUSUAL_PAYMENT


def test_lone_nine_is_caution_with_rescore():
    d = DialState()
    d.apply(r(4), True)
    tier = d.apply(r(9, RedFlag.INFO_FISHING, RedFlag.URGENCY), True)
    assert tier == Tier.CAUTION
    assert d.rescore_now


def test_stop_falls_back_slowly():
    d = DialState()
    d.apply(r(8, RedFlag.INFO_FISHING, RedFlag.URGENCY), True)
    d.apply(r(9, RedFlag.INFO_FISHING, RedFlag.URGENCY), True)
    assert d.tier == Tier.STOP
    d.apply(r(4), True)
    assert d.tier == Tier.STOP
    d.apply(r(3), True)
    assert d.tier == Tier.CAUTION
    assert d.max_score == 9


def test_failure_is_unknown_then_restores():
    d = DialState()
    d.apply(r(6, RedFlag.URGENCY), True)
    assert d.tier == Tier.CAUTION
    assert d.apply_failure() == Tier.UNKNOWN
    assert d.consecutive_failures == 1
    d.apply(r(6, RedFlag.URGENCY), True)
    assert d.tier == Tier.CAUTION
    assert d.consecutive_failures == 0


def test_score_clamped_and_flags_deduped():
    res = ScoreResult(
        score=47,
        reasoning="x" * 500,
        red_flags=["urgency", "URGENCY", "bogus"],
        provider="p",
        model="m",
    )
    assert res.score == 10
    assert len(res.reasoning) == 240
    assert res.red_flags == [RedFlag.URGENCY]
