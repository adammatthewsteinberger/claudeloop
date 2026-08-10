from __future__ import annotations

from autoclaude.infrastructure.agent.translate import TurnAccumulator, _to_datetime


def test_to_datetime_none_stays_none() -> None:
    assert _to_datetime(None) is None


def test_to_datetime_seconds_form_10_digits() -> None:
    # A plausible ~10-digit seconds-since-epoch value.
    result = _to_datetime(1786328953)
    assert result is not None
    assert 2020 <= result.year <= 2030


def test_to_datetime_milliseconds_form_13_digits() -> None:
    # The digit-count heuristic ported from the legacy script's resetsAt
    # handling — the same ambiguity that turned out to be real for
    # SDKSessionInfo.last_modified (see test_catalog.py).
    result = _to_datetime(1786328953799)
    assert result is not None
    assert 2020 <= result.year <= 2030


def test_accumulator_empty_build_is_available_with_no_verdict() -> None:
    accumulator = TurnAccumulator()
    outcome = accumulator.build()
    assert outcome.verdict is None
    assert outcome.output_text == ""
    assert outcome.session_id is None
    assert outcome.cost_usd == 0.0


def test_accumulator_feed_ignores_unrecognized_message_types() -> None:
    accumulator = TurnAccumulator()
    accumulator.feed(object())  # not RateLimitEvent/AssistantMessage/ResultMessage
    outcome = accumulator.build()
    assert outcome.output_text == ""
