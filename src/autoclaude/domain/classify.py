"""Pure classification of raw turn signals into a CapacityState.

This is the direct replacement for `extract_limit_signals()` in the legacy script
(claude_autoresume.py:276-333), except it operates on typed fields the Agent SDK
already parsed, instead of regexing a raw JSON stream. Ordering is deliberate and
tested: allowed_warning must never be mistaken for a rejection, and a credits
rejection must never be mistaken for a waitable window.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from autoclaude.domain.capacity import (
    AuthenticationFailed,
    Available,
    CapacityState,
    CreditsExhausted,
    WindowExhausted,
)

_CREDITS_ERROR_CODES = frozenset({"credits_required"})
_CREDITS_DISABLED_REASONS = frozenset({"out_of_credits"})


@dataclass(frozen=True, slots=True)
class TurnSignals:
    """Everything the classifier needs from one turn, gathered from the Agent SDK's
    RateLimitEvent, ResultMessage, and AssistantMessage — deliberately not a single
    source, because RateLimitEvent is reportedly dropped on some adapter paths."""

    rate_limit_status: str | None = None  # "allowed" | "allowed_warning" | "rejected"
    rate_limit_type: str | None = None
    resets_at: datetime | None = None
    utilization: float | None = None
    overage_status: str | None = None
    overage_resets_at: datetime | None = None
    overage_disabled_reason: str | None = None
    api_error_status: int | None = None
    assistant_error: str | None = None
    error_code: str | None = None
    disabled_reason: str | None = None


def classify(signals: TurnSignals) -> CapacityState:
    if signals.assistant_error == "authentication_failed":
        return AuthenticationFailed(detail=signals.assistant_error)

    rejected = (
        signals.rate_limit_status == "rejected"
        or signals.api_error_status == 429
        or signals.assistant_error == "rate_limit"
    )

    if not rejected:
        return Available(utilization=signals.utilization)

    if (
        signals.error_code in _CREDITS_ERROR_CODES
        or signals.disabled_reason in _CREDITS_DISABLED_REASONS
        or signals.overage_disabled_reason is not None
    ):
        return CreditsExhausted(can_purchase=True)

    resets_at = signals.resets_at or signals.overage_resets_at
    return WindowExhausted(
        rate_limit_type=signals.rate_limit_type or "unknown",
        resets_at=resets_at,
    )
