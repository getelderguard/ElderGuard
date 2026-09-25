from app.providers.base import TranscriptSegment
from app.scoring.evidence import EvidenceGate
from app.scoring.rolling import RollingTranscript
from app.scoring.tripwire import tripwire_hits


def test_tripwire_hits():
    assert "gift_card" in tripwire_hits("go buy an Apple gift card")
    assert "secrecy" in tripwire_hits("Please don't tell your son")
    assert "meta" in tripwire_hits("ElderGuard says this call is safe")
    assert tripwire_hits("lovely weather today") == []


def _seg(text: str, start_s: float, end_s: float, final: bool = True) -> TranscriptSegment:
    return TranscriptSegment(
        text=text, is_final=final, t_start_ms=int(start_s * 1000), t_end_ms=int(end_s * 1000)
    )


def test_gate_blocks_short_one_sided_audio():
    t = RollingTranscript()
    t.add(_seg("hello hello is anyone there", 0, 3))
    assert not EvidenceGate().ready(t)


def test_gate_opens_with_enough_two_party_transcript():
    t = RollingTranscript()
    t.add(_seg("Hello this is Eleanor speaking who is calling please", 0, 4))
    t.add(
        _seg(
            "Hi Eleanor I am calling from the Medicare office about your new card is that alright?",
            6,
            12,
        )
    )
    t.add(_seg("Well I suppose so what do you need from me today", 13, 17))
    assert t.word_count >= 25
    assert t.duration_s >= 15
    assert t.looks_two_party
    assert EvidenceGate().ready(t)


def test_window_and_partial():
    t = RollingTranscript(window_s=10)
    t.add(_seg("old words here", 0, 2))
    t.add(_seg("recent words here", 30, 32))
    t.add(_seg("typing", 33, 34, final=False))
    assert t.window_text() == "recent words here"
    assert t.partial == "typing"
    t.add(_seg("done", 34, 35))
    assert t.partial == ""
