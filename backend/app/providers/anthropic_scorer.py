"""Claude as a bounded scam scorer: cached rubric, structured output, low effort, hard timeout."""

from __future__ import annotations

import time
from typing import Any

import anthropic
from pydantic import BaseModel, Field

from app.providers.base import (
    ProviderBadOutput,
    ProviderRefused,
    ProviderUnavailable,
    RedFlag,
    ScoreResult,
    ScoringContext,
    Usage,
)
from app.scoring.prompts import SCAM_SCORING_SYSTEM_PROMPT, build_user_message


class _ScoreOut(BaseModel):
    score: int = Field(description="0 to 10")
    reasoning: str = Field(description="One short sentence")
    red_flags: list[RedFlag] = Field(default_factory=list)


class AnthropicScorer:
    name = "anthropic"

    def __init__(
        self,
        api_key: str | None,
        model: str = "claude-sonnet-5",
        effort: str = "low",
        max_tokens: int = 400,
        client: Any | None = None,
    ) -> None:
        self.model = model
        self.effort = effort
        self.max_tokens = max_tokens
        self._client = client or anthropic.AsyncAnthropic(api_key=api_key)

    async def score(self, ctx: ScoringContext, timeout_s: float) -> ScoreResult:
        t0 = time.monotonic()
        try:
            response = await self._client.with_options(
                timeout=timeout_s, max_retries=0
            ).messages.parse(
                model=self.model,
                max_tokens=self.max_tokens,
                system=[
                    {
                        "type": "text",
                        "text": SCAM_SCORING_SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": build_user_message(ctx)}],
                output_format=_ScoreOut,
                output_config={"effort": self.effort},
            )
        except anthropic.APITimeoutError as e:
            raise ProviderUnavailable(f"anthropic timeout: {e}") from e
        except anthropic.RateLimitError as e:
            raise ProviderUnavailable(f"anthropic rate limited: {e}") from e
        except anthropic.APIStatusError as e:
            raise ProviderUnavailable(f"anthropic status {e.status_code}: {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise ProviderUnavailable(f"anthropic connection error: {e}") from e

        latency_ms = int((time.monotonic() - t0) * 1000)
        if response.stop_reason == "refusal":
            raise ProviderRefused("anthropic refused the request")
        parsed = getattr(response, "parsed_output", None)
        if parsed is None:
            raise ProviderBadOutput("anthropic returned no parsable output")

        u = response.usage
        usage = Usage(
            input_tokens=getattr(u, "input_tokens", 0) or 0,
            output_tokens=getattr(u, "output_tokens", 0) or 0,
            cache_read_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
            cache_write_tokens=getattr(u, "cache_creation_input_tokens", 0) or 0,
        )
        return ScoreResult(
            score=parsed.score,
            reasoning=parsed.reasoning,
            red_flags=parsed.red_flags,
            provider=self.name,
            model=self.model,
            latency_ms=latency_ms,
            usage=usage,
        )
