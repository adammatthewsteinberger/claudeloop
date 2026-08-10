# Ports and adapters (planned — milestone M2+)

The `application/` and `infrastructure/` layers are scaffolded (the package
directories and `__init__.py` files exist so the `import-linter` contracts in
`pyproject.toml` are checkable today) but not yet implemented. This page
documents the **planned shape**, taken from
[`../plans/architecture-and-roadmap.md`](../plans/architecture-and-roadmap.md),
so contributors building M2 have a stable target and reviewers have
something concrete to check new code against.

## Why ports are `Protocol`, not `ABC`

`application/ports.py` will define every port as a `typing.Protocol`, not an
abstract base class. Two reasons:

1. **Structural typing keeps `application/` free of any import from
   `infrastructure/`.** A `Protocol` describes a shape; nothing has to
   inherit from it. `import-linter`'s "infrastructure only reachable from
   bootstrap" contract would reject an ABC-based design the moment a
   concrete adapter needed to `from autoclaude.application.ports import
   AgentGatewayBase` — with `Protocol`, the adapter simply implements the
   right methods and duck-types into place.
2. **Fakes for tests are trivial.** A `FakeAgentGateway` used in
   `tests/application/` doesn't need to inherit from anything either; it
   just needs the right method signatures, which `mypy --strict` verifies
   against the `Protocol` at type-check time.

## Planned ports (`application/ports.py`)

| Port | Responsibility | Real adapter (planned) | Fake (planned) |
|---|---|---|---|
| `AgentGateway` | Send a turn to a live `ClaudeSDKClient` session, yield typed events back | `infrastructure/agent/gateway.py` | `FakeAgentGateway` — replays a scripted event sequence |
| `CapacityProbe` | Run the cheap, throwaway turn used while waiting | `infrastructure/agent/probe.py` | scripted `CapacityState` sequence |
| `SessionCatalog` | List/resolve sessions via the SDK's `list_sessions()` / `get_session_info()` | `infrastructure/agent/session_catalog.py` | in-memory list of `SessionRef` |
| `ApiGateway` | Invoke a generated REST command against `anthropic.Anthropic()` | `infrastructure/api/gateway.py` | records the call, returns a canned response |
| `Clock` | `now()` | `infrastructure/clock.py` (`datetime.now`) | `FakeClock` — settable, doesn't advance on its own |
| `Sleeper` | `await sleep_until(instant)` | real `anyio.sleep` | `FakeSleeper` — advances the paired `FakeClock` instantly, records what it was asked to wait for |
| `ProgressReporter` | Human-readable progress to the console | Rich-based console adapter | records calls |
| `AuditLog` | Append-only JSONL of every raw event | `infrastructure/audit.py` | in-memory list |
| `Notifier` | Tell a human something needs attention (credits exhausted, etc.) | stdout + optional webhook | records calls |
| `RunStateStore` | Persist run state so a killed run is resumable | `infrastructure/state.py` | in-memory dict |
| `SessionLock` | Advisory file lock preventing two runners driving one session | `infrastructure/lock.py` | in-memory flag |

## Why `FakeClock`/`FakeSleeper`, not `unittest.mock` or real sleeping

The waiting policy in `domain/waiting.py` is designed around instants, not
durations, precisely so the application-layer tests never need to sleep for
real. A `FakeClock` holds a settable "now"; `FakeSleeper.sleep_until(instant)`
jumps the paired clock straight to `instant` instead of blocking. This is
what lets a test simulate a **seven-day rate-limit wait, or a credit-top-up
scenario with several failed probes before success, in microseconds of real
wall-clock test time** — see
[`../contributing/testing.md`](../contributing/testing.md) for the pattern
and why `unittest.mock.patch("time.sleep")` was rejected in favor of it (a
real port + fake beats patching a stdlib call every test file has to
remember to do consistently).

## The composition root (`bootstrap.py`)

`bootstrap.py` is the **only** module permitted to import from every layer
at once. Its job, once M2 lands, is a single wiring function:

```python
def build_runner(config: RunnerConfig) -> AutonomousRunner:
    """Wire concrete infrastructure adapters into the AutonomousRunner's ports."""
```

`cli/` commands call into `bootstrap.build_runner(...)` and then drive the
returned `AutonomousRunner` — they never construct an
`infrastructure.agent.gateway.ClaudeAgentGateway` directly. This is the seam
that makes it possible to swap an adapter (say, a different `Notifier`
backend) without touching `application/` or `cli/` at all.
