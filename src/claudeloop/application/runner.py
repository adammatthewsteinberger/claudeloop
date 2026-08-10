"""AutonomousRunner — executes domain.loop's pure Decisions against real ports.

Contains NO capacity or completion logic of its own. Every "is this waitable",
"how long do we wait", "is the task done" question is answered by domain/ before
this class ever sees it; this class only performs the I/O domain/loop.py decided
was needed and feeds the result back in."""

from __future__ import annotations

from claudeloop.application.dto import RunResult, TurnOutcome
from claudeloop.application.ports import (
    AgentGateway,
    AuditLog,
    CapacityProbe,
    Clock,
    ProgressReporter,
    Sleeper,
)
from claudeloop.domain.budget import Budget, BudgetLedger
from claudeloop.domain.capacity import CapacityState
from claudeloop.domain.classify import classify
from claudeloop.domain.completion import CompletionVerdict, evaluate
from claudeloop.domain.loop import (
    Finish,
    Phase,
    RunState,
    ScheduleProbe,
    SendTurn,
    decide_after_probe,
    decide_after_turn,
    decide_preflight,
    start,
)
from claudeloop.domain.waiting import DEFAULT_WAIT_POLICY_CONFIG, WaitPolicyConfig

_DEFAULT_BUDGET = Budget()


class AutonomousRunner:
    def __init__(
        self,
        *,
        agent_gateway: AgentGateway,
        capacity_probe: CapacityProbe,
        clock: Clock,
        sleeper: Sleeper,
        audit_log: AuditLog,
        progress: ProgressReporter,
        budget: Budget = _DEFAULT_BUDGET,
        wait_policy: WaitPolicyConfig = DEFAULT_WAIT_POLICY_CONFIG,
        done_marker: str | None = None,
    ) -> None:
        self._gateway = agent_gateway
        self._probe = capacity_probe
        self._clock = clock
        self._sleeper = sleeper
        self._audit = audit_log
        self._progress = progress
        self._budget = budget
        self._wait_policy = wait_policy
        self._done_marker = done_marker

    async def run(self, *, initial_prompt: str, continue_prompt: str) -> RunResult:
        """Drive one run to completion: send `initial_prompt` first, then
        `continue_prompt` on every subsequent SendTurn."""
        state = start(BudgetLedger(budget=self._budget))
        session_id: str | None = None
        first_turn = True
        attempt = 0

        preflight_outcome = await self._probe.probe()
        state, decision = decide_preflight(
            state,
            self._verdict_capacity(preflight_outcome),
            now=self._clock.now(),
            config=self._wait_policy,
        )
        self._audit.record("preflight", {"phase": state.phase.name})

        while True:
            if isinstance(decision, SendTurn):
                attempt += 1
                prompt = initial_prompt if first_turn else continue_prompt
                first_turn = False
                self._progress.turn_sent(attempt=attempt)
                outcome = await self._gateway.send_turn(prompt)
                session_id = outcome.session_id or session_id
                capacity = classify(outcome.signals)
                verdict = self._completion_verdict(outcome)
                self._audit.record(
                    "turn", {"attempt": attempt, "capacity": type(capacity).__name__}
                )
                state, decision = decide_after_turn(
                    state,
                    capacity=capacity,
                    verdict=verdict,
                    now=self._clock.now(),
                    config=self._wait_policy,
                )
            elif isinstance(decision, ScheduleProbe):
                self._progress.waiting(reason=state.phase.name, until=decision.at)
                self._audit.record("waiting", {"until": decision.at.isoformat()})
                await self._sleeper.sleep_until(decision.at)
                probe_outcome = await self._probe.probe()
                state, decision = decide_after_probe(
                    state,
                    self._verdict_capacity(probe_outcome),
                    now=self._clock.now(),
                    config=self._wait_policy,
                )
            else:
                # RunProbe is a declared member of domain.loop.Decision but no
                # decide_* function currently produces it standalone — probing
                # is folded into the ScheduleProbe branch above (schedule, wait,
                # then probe). Same unreachable-by-construction pattern as
                # domain.loop.Phase.PROBING; see that module's own exhaustiveness
                # asserts for the precedent this follows.
                assert isinstance(decision, Finish)  # nosec B101
                await self._gateway.close()
                self._progress.finished(success=decision.success, reason=decision.reason)
                self._audit.record(
                    "finished", {"success": decision.success, "reason": decision.reason}
                )
                return RunResult(
                    success=decision.success,
                    reason=decision.reason,
                    session_id=session_id,
                    turns_spent=state.ledger.turns_spent,
                    dollars_spent=state.ledger.dollars_spent,
                )

    def _verdict_capacity(self, outcome: TurnOutcome) -> CapacityState:
        return classify(outcome.signals)

    def _completion_verdict(self, outcome: TurnOutcome) -> CompletionVerdict:
        kwargs = {"done_marker": self._done_marker} if self._done_marker else {}
        return evaluate(structured=outcome.verdict, output_text=outcome.output_text, **kwargs)


__all__ = ["AutonomousRunner", "RunState", "Phase"]
