"""Translates raw claude_agent_sdk messages into the typed TurnSignals /
StructuredVerdict / TurnOutcome shapes domain/ and application/ operate on.

Reads THREE independent SDK signals — RateLimitEvent, ResultMessage, and
AssistantMessage — never RateLimitEvent alone. See
docs/architecture/decisions/0002-agent-sdk-over-subprocess.md."""

from __future__ import annotations

from datetime import datetime

from claude_agent_sdk import (
    AssistantMessage,
    RateLimitEvent,
    ResultMessage,
    TextBlock,
)

from claudeloop.application.dto import TurnOutcome
from claudeloop.domain.classify import TurnSignals
from claudeloop.domain.completion import StructuredVerdict


class TurnAccumulator:
    """Collects one turn's worth of SDK messages (everything from a prompt send
    to the terminating ResultMessage) and reduces them to a TurnOutcome."""

    def __init__(self) -> None:
        self._rate_limit_status: str | None = None
        self._rate_limit_type: str | None = None
        self._resets_at: int | None = None  # unix timestamp; converted in build()
        self._utilization: float | None = None
        self._overage_status: str | None = None
        self._overage_resets_at: int | None = None  # unix timestamp; converted in build()
        self._overage_disabled_reason: str | None = None
        self._api_error_status: int | None = None
        self._assistant_error: str | None = None
        self._error_code: str | None = None
        self._disabled_reason: str | None = None
        self._text_parts: list[str] = []
        self._session_id: str | None = None
        self._cost_usd: float = 0.0
        self._structured: dict[str, object] | None = None
        self._raw_events: list[dict[str, object]] = []

    def feed(self, message: object) -> None:
        if isinstance(message, RateLimitEvent):
            info = message.rate_limit_info
            self._rate_limit_status = info.status
            self._rate_limit_type = info.rate_limit_type
            self._resets_at = info.resets_at
            self._utilization = info.utilization
            self._overage_status = info.overage_status
            self._overage_resets_at = info.overage_resets_at
            self._overage_disabled_reason = info.overage_disabled_reason
            self._session_id = message.session_id or self._session_id
        elif isinstance(message, AssistantMessage):
            self._session_id = message.session_id or self._session_id
            if message.error is not None:
                self._assistant_error = str(message.error)
            for block in message.content:
                if isinstance(block, TextBlock):
                    self._text_parts.append(block.text)
        elif isinstance(message, ResultMessage):
            self._session_id = message.session_id or self._session_id
            if message.api_error_status is not None:
                self._api_error_status = message.api_error_status
            if message.total_cost_usd is not None:
                self._cost_usd = message.total_cost_usd
            if message.result:
                self._text_parts.append(message.result)
            if isinstance(message.structured_output, dict):
                self._structured = message.structured_output
            errors = message.errors or []
            for err in errors:
                err_str = str(err)
                if "credits_required" in err_str:
                    self._error_code = "credits_required"
                if "out_of_credits" in err_str:
                    self._disabled_reason = "out_of_credits"

    def build(self) -> TurnOutcome:
        signals = TurnSignals(
            rate_limit_status=self._rate_limit_status,
            rate_limit_type=self._rate_limit_type,
            resets_at=_to_datetime(self._resets_at),
            utilization=self._utilization,
            overage_status=self._overage_status,
            overage_resets_at=_to_datetime(self._overage_resets_at),
            overage_disabled_reason=self._overage_disabled_reason,
            api_error_status=self._api_error_status,
            assistant_error=self._assistant_error,
            error_code=self._error_code,
            disabled_reason=self._disabled_reason,
        )
        verdict = None
        if self._structured is not None:
            raw_remaining = self._structured.get("remaining_work")
            items: list[object] = list(raw_remaining) if isinstance(raw_remaining, list) else []
            remaining_work = tuple(str(item) for item in items)
            raw_blocked_on = self._structured.get("blocked_on")
            blocked_on = str(raw_blocked_on) if raw_blocked_on is not None else None
            verdict = StructuredVerdict(
                complete=bool(self._structured.get("complete", False)),
                remaining_work=remaining_work,
                blocked_on=blocked_on,
                summary=str(self._structured.get("summary", "")),
            )
        return TurnOutcome(
            signals=signals,
            verdict=verdict,
            output_text="\n".join(self._text_parts),
            session_id=self._session_id,
            cost_usd=self._cost_usd,
            raw_events=tuple(self._raw_events),
        )


def _to_datetime(unix_timestamp: int | None) -> datetime | None:
    """Live testing found SDKSessionInfo.last_modified is milliseconds, not
    seconds, despite being documented only as "unix timestamp" (see
    infrastructure/agent/catalog.py). RateLimitInfo.resets_at carries the same
    vague documentation, so rather than assume a fixed unit here too, use the
    same digit-count heuristic the legacy script already needed for its
    resetsAt handling: ~10 digits is seconds, ~13 digits is milliseconds."""
    if unix_timestamp is None:
        return None
    seconds = unix_timestamp / 1000 if unix_timestamp >= 10_000_000_000 else unix_timestamp
    return datetime.fromtimestamp(seconds)


COMPLETION_OUTPUT_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "complete": {"type": "boolean"},
        "remaining_work": {"type": "array", "items": {"type": "string"}},
        "blocked_on": {"type": ["string", "null"]},
        "summary": {"type": "string"},
    },
    "required": ["complete"],
}
