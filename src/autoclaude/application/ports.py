"""Application ports — Protocols implemented by infrastructure/, never imported
from it. See docs/architecture/overview.md for the onion rule this enforces:
application/ knows the SHAPE of a collaborator, never its concrete type."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from autoclaude.application.dto import TurnOutcome
from autoclaude.domain.session import SessionRef


class Clock(Protocol):
    def now(self) -> datetime: ...


class Sleeper(Protocol):
    async def sleep_until(self, instant: datetime) -> None: ...


class AgentGateway(Protocol):
    """Wraps a live claude_agent_sdk.ClaudeSDKClient session. Deliberately NOT
    query() — see docs/architecture/decisions/0002-agent-sdk-over-subprocess.md
    for why query() cannot be used here (it raises after an error result and
    exits the process, where ClaudeSDKClient survives to be resumed)."""

    async def send_turn(self, prompt_text: str) -> TurnOutcome: ...
    async def close(self) -> None: ...


class CapacityProbe(Protocol):
    async def probe(self) -> TurnOutcome: ...


class SessionCatalog(Protocol):
    def most_recent(self, cwd: str) -> SessionRef | None: ...
    def list_all(self, cwd: str | None = None) -> list[SessionRef]: ...


class ProgressReporter(Protocol):
    def turn_sent(self, *, attempt: int) -> None: ...
    def waiting(self, *, reason: str, until: datetime) -> None: ...
    def finished(self, *, success: bool, reason: str) -> None: ...


class AuditLog(Protocol):
    def record(self, event_type: str, payload: dict[str, Any]) -> None: ...


class Notifier(Protocol):
    def notify(self, message: str) -> None: ...


class RunStateStore(Protocol):
    def save(self, run_id: str, state: dict[str, Any]) -> None: ...
    def load(self, run_id: str) -> dict[str, Any] | None: ...


class SessionLock(Protocol):
    def acquire(self, session_id: str) -> bool: ...
    def release(self, session_id: str) -> None: ...


class ApiGateway(Protocol):
    """Declared now; implemented in M4 alongside the generated REST surface.
    See docs/architecture/decisions/0006-generated-rest-surface-not-hand-written.md."""

    def invoke(self, method_path: str, **kwargs: Any) -> Any: ...
