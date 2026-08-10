"""Real fakes (not unittest.mock.Mock) implementing application/ports.py's
Protocols, so mypy --strict checks them against the port shape and no test
ever calls time.sleep() for real. See docs/contributing/testing.md."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from autoclaude.application.dto import TurnOutcome
from autoclaude.domain.classify import TurnSignals
from autoclaude.domain.completion import StructuredVerdict


class FakeClock:
    def __init__(self, start: datetime) -> None:
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance_to(self, instant: datetime) -> None:
        self._now = instant


class FakeSleeper:
    """sleep_until() jumps the paired FakeClock straight to the target
    instant instead of blocking — this is what lets a test simulate a
    multi-day wait in microseconds of real wall-clock time."""

    def __init__(self, clock: FakeClock) -> None:
        self._clock = clock
        self.wait_log: list[datetime] = []

    async def sleep_until(self, instant: datetime) -> None:
        self.wait_log.append(instant)
        self._clock.advance_to(instant)


@dataclass(frozen=True, slots=True)
class ScriptedTurn:
    signals: TurnSignals = field(default_factory=TurnSignals)
    verdict: StructuredVerdict | None = None
    output_text: str = ""
    session_id: str = "fake-session-id"


class FakeAgentGateway:
    """Replays a scripted sequence of TurnOutcomes, one per send_turn() call.
    Raises IndexError (a clear test failure) if more turns are requested than
    were scripted — a runaway loop should fail loudly, not hang."""

    def __init__(self, script: list[ScriptedTurn]) -> None:
        self._script = list(script)
        self.sent_prompts: list[str] = []
        self.closed = False

    async def send_turn(self, prompt_text: str) -> TurnOutcome:
        self.sent_prompts.append(prompt_text)
        turn = self._script.pop(0)
        return TurnOutcome(
            signals=turn.signals,
            verdict=turn.verdict,
            output_text=turn.output_text,
            session_id=turn.session_id,
        )

    async def close(self) -> None:
        self.closed = True


class FakeCapacityProbe:
    """Replays a scripted sequence of TurnSignals, one per probe() call —
    including the preflight call, which is always the first one consumed."""

    def __init__(self, script: list[TurnSignals]) -> None:
        self._script = list(script)

    async def probe(self) -> TurnOutcome:
        signals = self._script.pop(0)
        return TurnOutcome(signals=signals, verdict=None, output_text="", session_id=None)


class FakeAuditLog:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    def record(self, event_type: str, payload: dict[str, object]) -> None:
        self.events.append((event_type, payload))


class FakeProgressReporter:
    def __init__(self) -> None:
        self.turns: list[int] = []
        self.waits: list[tuple[str, datetime]] = []
        self.finishes: list[tuple[bool, str]] = []

    def turn_sent(self, *, attempt: int) -> None:
        self.turns.append(attempt)

    def waiting(self, *, reason: str, until: datetime) -> None:
        self.waits.append((reason, until))

    def finished(self, *, success: bool, reason: str) -> None:
        self.finishes.append((success, reason))


def available_signals() -> TurnSignals:
    return TurnSignals()


def credits_exhausted_signals() -> TurnSignals:
    return TurnSignals(rate_limit_status="rejected", error_code="credits_required")


def window_exhausted_signals(*, resets_at: datetime | None = None) -> TurnSignals:
    return TurnSignals(
        rate_limit_status="rejected", rate_limit_type="five_hour", resets_at=resets_at
    )


DONE_VERDICT = StructuredVerdict(complete=True, summary="all done")
CONTINUE_VERDICT = StructuredVerdict(complete=False, remaining_work=("more work",))


def five_minutes(clock: FakeClock) -> datetime:
    return clock.now() + timedelta(minutes=5)
