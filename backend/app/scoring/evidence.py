"""Evidence gate: no tier may change until there is enough two-party transcript to judge."""

from __future__ import annotations

from dataclasses import dataclass

from app.scoring.rolling import RollingTranscript


@dataclass(frozen=True)
class EvidenceGate:
    min_words: int = 25
    min_seconds: float = 15.0

    def ready(self, transcript: RollingTranscript) -> bool:
        return (
            transcript.word_count >= self.min_words
            and transcript.duration_s >= self.min_seconds
            and transcript.looks_two_party
        )
