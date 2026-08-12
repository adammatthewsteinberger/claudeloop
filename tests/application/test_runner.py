from datetime import datetime, timedelta, timezone

from claudeloop.application.runner import AutonomousRunner
from claudeloop.domain.budget import Budget
from claudeloop.domain.classify import TurnSignals
from claudeloop.domain.completion import StructuredVerdict
from claudeloop.domain.control import PromptDeferredCommand, PromptNowCommand, StopCommand
from claudeloop.domain.waiting import WaitPolicyConfig
from tests.application.fakes import (
    CONTINUE_VERDICT,
    DONE_VERDICT,
    FakeAgentGateway,
    FakeAuditLog,
    FakeCapacityProbe,
    FakeClock,
    FakeEventSink,
    FakeNotifier,
    FakeProgressReporter,
    FakeRunControl,
    FakeSavePointStore,
    FakeSessionLock,
    FakeSleeper,
    FakeStateStore,
    ScriptedTurn,
    available_signals,
    credits_exhausted_signals,
    window_exhausted_signals,
)

NOW = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)
_DEFAULT_BUDGET = Budget()
_DEFAULT_WAIT_POLICY = WaitPolicyConfig()


def make_runner(
    *,
    turns: list[ScriptedTurn],
    probes: list,
    budget: Budget = _DEFAULT_BUDGET,
    wait_policy: WaitPolicyConfig = _DEFAULT_WAIT_POLICY,
    run_control: FakeRunControl | None = None,
    notifier: FakeNotifier | None = None,
    save_points: FakeSavePointStore | None = None,
) -> tuple[
    AutonomousRunner,
    FakeAgentGateway,
    FakeAuditLog,
    FakeProgressReporter,
    FakeSleeper,
    FakeNotifier,
    FakeEventSink,
]:
    clock = FakeClock(start=NOW)
    sleeper = FakeSleeper(clock)
    gateway = FakeAgentGateway(turns)
    probe = FakeCapacityProbe(probes)
    audit = FakeAuditLog()
    progress = FakeProgressReporter()
    notifier = notifier or FakeNotifier()
    events = FakeEventSink()
    runner = AutonomousRunner(
        agent_gateway=gateway,
        capacity_probe=probe,
        clock=clock,
        sleeper=sleeper,
        audit_log=audit,
        progress=progress,
        budget=budget,
        wait_policy=wait_policy,
        done_marker="TEST_DONE_MARKER",
        run_id="test-run",
        notifier=notifier,
        run_control=run_control or FakeRunControl(),
        event_sink=events,
        state_store=FakeStateStore(),
        session_lock=FakeSessionLock(),
        save_points=save_points or FakeSavePointStore(),
    )
    return runner, gateway, audit, progress, sleeper, notifier, events


async def test_preflight_available_then_done_in_one_turn() -> None:
    runner, gateway, _audit, progress, _sleeper, _n, _e = make_runner(
        turns=[ScriptedTurn(signals=available_signals(), verdict=DONE_VERDICT)],
        probes=[available_signals()],
    )
    result = await runner.run(initial_prompt="do the thing", continue_prompt="continue")
    assert result.success is True
    assert result.reason == "all done"
    assert result.turns_spent == 1
    assert gateway.closed is True
    assert gateway.sent_prompts == ["do the thing"]
    assert progress.finishes == [(True, "all done")]


async def test_continue_verdict_sends_a_second_turn_with_continue_prompt() -> None:
    runner, gateway, _audit, _progress, _sleeper, _n, _e = make_runner(
        turns=[
            ScriptedTurn(signals=available_signals(), verdict=CONTINUE_VERDICT),
            ScriptedTurn(signals=available_signals(), verdict=DONE_VERDICT),
        ],
        probes=[available_signals()],
    )
    result = await runner.run(initial_prompt="start", continue_prompt="keep going")
    assert result.success is True
    assert result.turns_spent == 2
    assert gateway.sent_prompts == ["start", "keep going"]


async def test_limit_outranks_a_done_verdict_on_the_same_turn() -> None:
    """The single most important invariant, exercised through the real
    AutonomousRunner rather than just domain.loop directly: a turn that hits
    a rate limit must never be treated as complete, even if it also carries
    a Done-shaped verdict."""
    runner, _gateway, _audit, _progress, sleeper, _n, _e = make_runner(
        turns=[
            ScriptedTurn(
                signals=window_exhausted_signals(resets_at=NOW + timedelta(minutes=1)),
                verdict=DONE_VERDICT,
            ),
            ScriptedTurn(signals=available_signals(), verdict=DONE_VERDICT),
        ],
        probes=[available_signals(), available_signals()],
        wait_policy=WaitPolicyConfig(reset_grace=timedelta(seconds=1)),
    )
    result = await runner.run(initial_prompt="start", continue_prompt="keep going")
    assert result.success is True
    assert len(sleeper.wait_log) >= 1
    assert result.turns_spent == 2


async def test_credit_topup_resumes_after_several_failed_probes_end_to_end() -> None:
    notifier = FakeNotifier()
    runner, gateway, _audit, _progress, sleeper, notifier, _e = make_runner(
        turns=[ScriptedTurn(signals=available_signals(), verdict=DONE_VERDICT)],
        probes=[
            credits_exhausted_signals(),
            credits_exhausted_signals(),
            credits_exhausted_signals(),
            credits_exhausted_signals(),
            available_signals(),
        ],
        wait_policy=WaitPolicyConfig(credits_probe_interval=timedelta(seconds=1)),
        notifier=notifier,
    )
    result = await runner.run(initial_prompt="start", continue_prompt="keep going")
    assert result.success is True
    assert len(sleeper.wait_log) >= 4
    assert gateway.sent_prompts == ["start"]
    assert any("credits exhausted" in m for m in notifier.messages)


async def test_authentication_failure_is_terminal_and_never_retried() -> None:
    runner, gateway, _audit, progress, sleeper, _n, _e = make_runner(
        turns=[],
        probes=[TurnSignals(assistant_error="authentication_failed")],
    )
    result = await runner.run(initial_prompt="start", continue_prompt="keep going")
    assert result.success is False
    assert result.reason == "authentication failed"
    assert sleeper.wait_log == []
    assert gateway.sent_prompts == []
    assert progress.finishes == [(False, "authentication failed")]


async def test_budget_exhaustion_stops_the_run_cleanly() -> None:
    runner, _gateway, _audit, _progress, _sleeper, _n, _e = make_runner(
        turns=[
            ScriptedTurn(signals=available_signals(), verdict=CONTINUE_VERDICT),
            ScriptedTurn(signals=available_signals(), verdict=CONTINUE_VERDICT),
        ],
        probes=[available_signals()],
        budget=Budget(max_turns=2),
    )
    result = await runner.run(initial_prompt="start", continue_prompt="keep going")
    assert result.success is False
    assert result.reason == "budget exhausted"
    assert result.turns_spent == 2


async def test_dollar_budget_uses_turn_cost() -> None:
    runner, _gateway, _audit, _progress, _sleeper, _n, _e = make_runner(
        turns=[
            ScriptedTurn(
                signals=available_signals(),
                verdict=CONTINUE_VERDICT,
                cost_usd=1.5,
            ),
        ],
        probes=[available_signals()],
        budget=Budget(max_dollars=1.0),
    )
    result = await runner.run(initial_prompt="start", continue_prompt="keep going")
    assert result.success is False
    assert result.reason == "budget exhausted"
    assert result.dollars_spent == 1.5


async def test_blocked_verdict_fails_with_the_stated_reason() -> None:
    blocked = StructuredVerdict(complete=False, blocked_on="missing MCP credentials")
    runner, _gateway, _audit, _progress, _sleeper, _n, _e = make_runner(
        turns=[ScriptedTurn(signals=available_signals(), verdict=blocked)],
        probes=[available_signals()],
    )
    result = await runner.run(initial_prompt="start", continue_prompt="keep going")
    assert result.success is False
    assert result.reason == "missing MCP credentials"


async def test_audit_log_records_every_phase_transition() -> None:
    runner, _gateway, audit, _progress, _sleeper, _n, _e = make_runner(
        turns=[ScriptedTurn(signals=available_signals(), verdict=DONE_VERDICT)],
        probes=[available_signals()],
    )
    await runner.run(initial_prompt="start", continue_prompt="keep going")
    event_types = [e[0] for e in audit.events]
    assert event_types == ["preflight", "turn", "finished"]


async def test_stop_command_ends_run_and_closes_gateway() -> None:
    control = FakeRunControl(script=[[StopCommand()]])
    summaries: list[str] = []
    runner, gateway, _a, _p, _s, _n, events = make_runner(
        turns=[ScriptedTurn(signals=available_signals(), verdict=DONE_VERDICT)],
        probes=[available_signals()],
        run_control=control,
    )
    runner._stop_summary_writer = lambda md: summaries.append(md) or "stop.md"
    result = await runner.run(initial_prompt="start", continue_prompt="keep going")
    assert result.success is False
    assert "stopped" in result.reason
    assert gateway.closed is True
    assert summaries
    assert any(e[0] == "control.stop" for e in events.events)


async def test_prompt_now_replaces_continue_prompt() -> None:
    control = FakeRunControl(
        script=[
            [],
            [PromptNowCommand(text="injected now")],
        ]
    )
    runner, gateway, _a, _p, _s, _n, _e = make_runner(
        turns=[
            ScriptedTurn(signals=available_signals(), verdict=CONTINUE_VERDICT),
            ScriptedTurn(signals=available_signals(), verdict=DONE_VERDICT),
        ],
        probes=[available_signals()],
        run_control=control,
    )
    result = await runner.run(initial_prompt="start", continue_prompt="keep going")
    assert result.success is True
    assert gateway.sent_prompts == ["start", "injected now"]


async def test_prompt_deferred_applies_at_natural_break() -> None:
    control = FakeRunControl(
        script=[
            [PromptDeferredCommand(text="later please")],
            [],
        ]
    )
    runner, gateway, _a, _p, _s, _n, _e = make_runner(
        turns=[
            ScriptedTurn(signals=available_signals(), verdict=CONTINUE_VERDICT),
            ScriptedTurn(signals=available_signals(), verdict=DONE_VERDICT),
        ],
        probes=[available_signals()],
        run_control=control,
    )
    result = await runner.run(initial_prompt="start", continue_prompt="keep going")
    assert result.success is True
    assert gateway.sent_prompts == ["start", "later please"]


async def test_stop_during_wait_interrupts_sleep() -> None:
    control = FakeRunControl(
        script=[
            [],  # loop start before first turn
            [],  # loop start entering ScheduleProbe
            [],  # first poll inside sleep — allow one chunk
            [StopCommand()],  # second poll inside sleep — stop
        ]
    )
    runner, gateway, _a, _p, sleeper, _n, _e = make_runner(
        turns=[
            ScriptedTurn(
                signals=window_exhausted_signals(resets_at=NOW + timedelta(hours=1)),
                verdict=CONTINUE_VERDICT,
            ),
        ],
        probes=[available_signals()],
        run_control=control,
        wait_policy=WaitPolicyConfig(reset_grace=timedelta(seconds=1)),
    )
    result = await runner.run(initial_prompt="start", continue_prompt="keep going")
    assert result.success is False
    assert "stopped" in result.reason
    assert gateway.closed is True
    assert len(sleeper.wait_log) >= 1
