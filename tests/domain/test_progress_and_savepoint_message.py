"""Tests for progress-wait helpers and savepoint Conventional Commits messages."""

from __future__ import annotations

from datetime import datetime, timezone

from claudeloop.domain.completion import evaluate
from claudeloop.domain.loop import Continue, decide_progress_delay
from claudeloop.domain.savepoint_message import format_savepoint_commit_message
from claudeloop.domain.waiting import (
    ProgressWaitConfig,
    is_wait_only_remaining_work,
    next_progress_wait_instant,
)

NOW = datetime(2026, 8, 13, tzinfo=timezone.utc)


def test_wait_only_heuristic() -> None:
    assert is_wait_only_remaining_work(())
    assert is_wait_only_remaining_work(("Wait for E2E suite", "still running flow 1"))
    assert not is_wait_only_remaining_work(("Fix the login button",))


def test_progress_wait_backoff_clamps() -> None:
    cfg = ProgressWaitConfig(initial_seconds=30, factor=2.0, ceiling_seconds=300)
    at0 = next_progress_wait_instant(now=NOW, streak=0, config=cfg)
    at10 = next_progress_wait_instant(now=NOW, streak=10, config=cfg)
    assert (at0 - NOW).total_seconds() == 30
    assert (at10 - NOW).total_seconds() == 300


def test_decide_progress_delay_none_when_tree_changed() -> None:
    assert (
        decide_progress_delay(
            verdict=Continue(remaining_work=("Waiting for suite",)),
            tree_changed=True,
            now=NOW,
            streak=0,
        )
        is None
    )


def test_decide_progress_delay_when_wait_only() -> None:
    delay = decide_progress_delay(
        verdict=Continue(remaining_work=("Waiting for suite",)),
        tree_changed=False,
        now=NOW,
        streak=0,
    )
    assert delay is not None
    assert (delay.at - NOW).total_seconds() == 30


def test_format_savepoint_message() -> None:
    subject, body = format_savepoint_commit_message(
        run_id="run1",
        attempt=3,
        verdict_name="Continue",
        summary="Restarted Metro with EXPO_PUBLIC_E2E",
        remaining_work=("Wait for suite",),
        changed_paths=("mobile/app.json",),
        label="turn-3",
    )
    assert subject.startswith("chore(claudeloop): turn 3 —")
    assert "Run: run1" in body
    assert "Attempt: 3" in body
    assert "mobile/app.json" in body


def test_empty_turn_soft_continue_then_blocked() -> None:
    first = evaluate(structured=None, output_text="", cost_usd=0.0, empty_turn_streak=0)
    assert isinstance(first, Continue)
    third = evaluate(structured=None, output_text="", cost_usd=0.0, empty_turn_streak=2)
    from claudeloop.domain.completion import Blocked

    assert isinstance(third, Blocked)
