from datetime import datetime, timedelta, timezone

from autoclaude.application.runner import AutonomousRunner
from autoclaude.domain.budget import Budget
from autoclaude.domain.classify import TurnSignals
from autoclaude.domain.completion import StructuredVerdict
from autoclaude.domain.waiting import WaitPolicyConfig
from tests.application.fakes import (
    CONTINUE_VERDICT,
    DONE_VERDICT,
    FakeAgentGateway,
    FakeAuditLog,
    FakeCapacityProbe,
    FakeClock,
    FakeProgressReporter,
    FakeSleeper,
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
) -> tuple[AutonomousRunner, FakeAgentGateway, FakeAuditLog, FakeProgressReporter, FakeSleeper]:
    clock = FakeClock(start=NOW)
    sleeper = FakeSleeper(clock)
    gateway = FakeAgentGateway(turns)
    probe = FakeCapacityProbe(probes)
    audit = FakeAuditLog()
    progress = FakeProgressReporter()
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
    )
    return runner, gateway, audit, progress, sleeper


async def test_preflight_available_then_done_in_one_turn() -> None:
    runner, gateway, _audit, progress, _sleeper = make_runner(
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
    runner, gateway, _audit, _progress, _sleeper = make_runner(
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
    runner, _gateway, _audit, _progress, sleeper = make_runner(
        turns=[
            # This turn claims Done AND hit a limit — the limit must win,
            # so the run must NOT finish here; it must wait, then send one
            # more real turn (below) once capacity returns.
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
    # succeeds via the second real turn, never treating the limited one as done
    assert result.success is True
    assert len(sleeper.wait_log) == 1  # it genuinely waited before resuming
    assert result.turns_spent == 2


async def test_credit_topup_resumes_after_several_failed_probes_end_to_end() -> None:
    """The scenario this project exists to handle: CreditsExhausted has no
    reset time, so only a probe loop — never a blind sleep — can notice a
    human topped up the account mid-wait."""
    runner, gateway, _audit, _progress, sleeper = make_runner(
        turns=[ScriptedTurn(signals=available_signals(), verdict=DONE_VERDICT)],
        probes=[
            credits_exhausted_signals(),  # preflight
            credits_exhausted_signals(),
            credits_exhausted_signals(),
            credits_exhausted_signals(),
            available_signals(),  # capacity restored
        ],
        wait_policy=WaitPolicyConfig(credits_probe_interval=timedelta(seconds=1)),
    )
    result = await runner.run(initial_prompt="start", continue_prompt="keep going")
    assert result.success is True
    assert len(sleeper.wait_log) == 4
    assert gateway.sent_prompts == ["start"]


async def test_authentication_failure_is_terminal_and_never_retried() -> None:
    runner, gateway, _audit, progress, sleeper = make_runner(
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
    runner, _gateway, _audit, _progress, _sleeper = make_runner(
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


async def test_blocked_verdict_fails_with_the_stated_reason() -> None:
    blocked = StructuredVerdict(complete=False, blocked_on="missing MCP credentials")
    runner, _gateway, _audit, _progress, _sleeper = make_runner(
        turns=[ScriptedTurn(signals=available_signals(), verdict=blocked)],
        probes=[available_signals()],
    )
    result = await runner.run(initial_prompt="start", continue_prompt="keep going")
    assert result.success is False
    assert result.reason == "missing MCP credentials"


async def test_audit_log_records_every_phase_transition() -> None:
    runner, _gateway, audit, _progress, _sleeper = make_runner(
        turns=[ScriptedTurn(signals=available_signals(), verdict=DONE_VERDICT)],
        probes=[available_signals()],
    )
    await runner.run(initial_prompt="start", continue_prompt="keep going")
    event_types = [e[0] for e in audit.events]
    assert event_types == ["preflight", "turn", "finished"]
