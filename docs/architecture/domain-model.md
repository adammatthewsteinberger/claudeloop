# Domain model reference

Every type below lives in `src/claudeloop/domain/`, has zero third-party
imports, and is fully covered by `tests/domain/`. This page documents what
each module contains and *why* it's shaped the way it is — for line-level API
docs, see the mkdocstrings-generated [reference](../reference/api.md).

## `errors.py` — the error hierarchy

```python
AutoclaudeError                    # base for every error claudeloop raises itself
├── InvalidPlanError               # a plan file couldn't be parsed into work items
├── InvalidSessionSelectorError    # a session selector is malformed
├── BudgetExceededError            # a run exceeded its turn/dollar/attempt budget
└── AuthenticationFailedError      # terminal — credentials invalid/revoked
```

Pure `Exception` subclasses, raised by `__post_init__` validators throughout
the rest of this module. Nothing here carries I/O state (no file handles, no
HTTP response objects) — just enough context to explain what was invalid.

## `plan.py` — `WorkPlan`, `PlanItem`

Parses a markdown handoff file into a `WorkPlan`: the raw text plus any
checkbox items found in it (`- [ ] ...` / `- [x] ...`, both bullet styles,
either case for `x`). A plan with no checkboxes is still valid — bare
free-text instructions — just with an empty `items` tuple.

```python
plan = WorkPlan.parse(markdown_text)
plan.remaining_items  # tuple[PlanItem, ...] — the ones not yet done
plan.is_fully_done  # True only if it HAS items and all are done
plan.with_items_marked_done(frozenset({"item text", ...}))  # new WorkPlan
```

`with_items_marked_done` is how a turn's structured `remaining_work` verdict
(see [`completion.py`](#completionpy-completionverdict) below) gets
reconciled back against the plan's own checklist between turns, so the audit
log can show *which* items are actually left rather than one boolean.

## `session.py` — `SessionRef` and the selector union

`SessionRef` is a resolved pointer to a Claude Code session (id, cwd, and
optional enrichment: last-modified time, git branch, first-prompt preview).

Three ways to *ask* for a session, modeled as a closed union rather than
optional/nullable fields on one class — the legacy script's three input
modes made explicit as types instead of `if prompt_file: ... elif
session_id: ... else: ...`:

```python
SessionSelector = PlanFileSelector | ExplicitSessionSelector | MostRecentSessionSelector
```

| Selector | Legacy equivalent |
|---|---|
| `PlanFileSelector(plan_path)` | `python3 claude_autoresume.py handoff.md` |
| `ExplicitSessionSelector(session_id)` | `python3 claude_autoresume.py --session-id <id>` |
| `MostRecentSessionSelector(cwd)` | no arguments — auto-detect the most recent session |

## `capacity.py` — `CapacityState`

The core insight this module encodes: **not every rejection is the same kind
of "no."** A five-hour rate-limit window and an empty credits balance both
surface as an HTTP 429, but only one of them will ever resolve by waiting.

```python
CapacityState = Available | WindowExhausted | CreditsExhausted | AuthenticationFailed
```

- **`Available(utilization: float | None)`** — capacity exists; spend a real
  turn. `utilization` is informational (from an `allowed_warning` signal) and
  must never itself block a turn.
- **`WindowExhausted(rate_limit_type, resets_at)`** — a
  `five_hour` / `seven_day` / `seven_day_opus` / `seven_day_sonnet` / `overage`
  window is rejected. `resets_at` is the trusted reset instant *when known* —
  it is `None`, not a guess, when the signal didn't carry one.
- **`CreditsExhausted(can_purchase: bool = True)`** — no token/time budget
  fixes this. There is **no `resets_at` field on this type at all** — that's
  deliberate, not an oversight, because a clock advancing can never resolve
  an empty credits balance. Only a human buying more can, which is why the
  waiting policy (below) treats this state completely differently.
- **`AuthenticationFailed(detail)`** — terminal. `is_waitable()` returns
  `False` only for this state; every other state is, by construction,
  something a wait-and-retry loop can eventually clear.

## `classify.py` — `TurnSignals` → `CapacityState`

This is the direct, tested replacement for `extract_limit_signals()` in
`legacy/claude_autoresume.py` (lines 276–333), which regex-matched raw
stream-json text against phrases like `"usage limit"` / `"try again later"`.
`classify()` instead operates on typed fields the Agent SDK has already
parsed:

```python
def classify(signals: TurnSignals) -> CapacityState: ...
```

`TurnSignals` deliberately gathers fields from **three different SDK
surfaces** — `RateLimitEvent`, `ResultMessage.api_error_status`, and
`AssistantMessage.error` — rather than trusting `RateLimitEvent` alone. The
Claude Code binary contains the string `[sdkMessageAdapter] Ignoring
rate_limit_event message`, suggesting that event is dropped on some adapter
paths; classification must not have a single point of failure.

**Ordering matters and is tested explicitly** (see
`tests/domain/test_classify.py`):

1. `assistant_error == "authentication_failed"` outranks everything —
   terminal, checked first, regardless of what else the turn carried.
2. `rate_limit_status == "allowed_warning"` is **not** a rejection. This is
   the exact false positive that caused multi-day cooldowns in the legacy
   script: `allowed_warning` carries a far-future weekly `resetsAt` just like
   a real rejection does, so a classifier that doesn't special-case it will
   misfire on ordinary healthy traffic.
3. A rejection (`status == "rejected"` OR `api_error_status == 429` OR
   `assistant_error == "rate_limit"`) is then split: credit signals
   (`error_code == "credits_required"`, `disabled_reason ==
   "out_of_credits"`, or a set `overage_disabled_reason`) win over a stray
   reset time — a `resets_at` present alongside a credits signal is ignored,
   because waiting can never fix that state regardless of what timestamp
   rode along with it.
4. Anything left is `WindowExhausted`, falling back to
   `rate_limit_type="unknown", resets_at=None` when the signal is thin.

## `completion.py` — `CompletionVerdict`

```python
CompletionVerdict = Done | Continue | Blocked
```

Primary source: a structured JSON verdict the model returns every turn via
`ClaudeAgentOptions.output_format`:

```json
{"complete": bool, "remaining_work": [str], "blocked_on": str | null, "summary": str}
```

`evaluate()` maps that (as a `StructuredVerdict`) to the union above, with
`blocked_on` outranking `complete` — a turn can't claim done and blocked at
once, and a non-null `blocked_on` **terminates the run as failed**. It is
only for true external/human blockers (credentials, billing, required human
decisions); waitable self-started work (background tasks, pending suites)
belongs in `remaining_work` with `blocked_on: null`. When `structured` is
`None` (older model, or structured output unsupported), it falls back to
substring-matching a legacy marker (`CLAUDELOOP_TASK_FULLY_COMPLETE` by
default) in the raw output text, exactly as `claude_autoresume.py` does
today — but only as a fallback, not the primary mechanism, because a marker
can collide with the user's own prompt text or appear inside a truncated
limit message. The run loop (below) never trusts a `Done` verdict over a
real capacity rejection, regardless of which detection path produced it.

## `waiting.py` — `WaitPolicyConfig` & `next_probe_instant()`

The direct replacement for `time.sleep(wait_seconds)` in the legacy script
(line 655). `next_probe_instant()` returns *the next instant to check again*
— never a single long sleep — because the whole point is noticing a mid-wait
credit top-up or an overage lift before a fixed deadline arrives.

```python
def next_probe_instant(
    state: CapacityState,
    *,
    now,
    started_waiting_at,
    probe_count,
    config: WaitPolicyConfig = ...,
) -> datetime: ...
```

Behavior by state:

- **`CreditsExhausted`** — exponential backoff from
  `credits_probe_interval` (default 120s) up to `credits_probe_ceiling`
  (default 600s), computed in float seconds and clamped *before*
  constructing a `timedelta` — an unclamped `interval * factor**probe_count`
  overflows `timedelta`'s ~2.7-million-year magnitude limit well within
  realistic probe counts, which a Hypothesis property test caught during
  development (see the property tests in `tests/domain/test_waiting.py`).
- **`WindowExhausted(resets_at=...)`** — probes at
  `min(resets_at + reset_grace, now + window_probe_interval)`. The
  `resets_at` bound is the expected path; the interval bound is what catches
  a top-up that lifts an overage-driven rejection *before* the window would
  naturally roll over — without it, a seven-day window's `resets_at` would
  mean waiting up to a week to notice capacity actually returned days ago.
- **`WindowExhausted(resets_at=None)`** — falls back to
  `window_probe_interval` alone.
- `config.max_wait`, when set, clamps every candidate instant to
  `started_waiting_at + max_wait`; `wait_exceeded()` is the corresponding
  "give up" check the run loop uses to fail rather than wait forever.

## `budget.py` — `Budget`, `BudgetLedger`

Immutable spend tracking for an unattended, potentially multi-day run.
`Budget` declares optional caps (`max_turns`, `max_dollars`, `max_attempts`);
`BudgetLedger` tracks consumption against it, and every spend
(`spend_turn()`, `spend_attempt()`) returns a **new** ledger rather than
mutating in place — the same immutability discipline as the rest of the
domain layer, which is what makes the run-loop state machine's transitions
pure functions.

## `loop.py` — the run-loop state machine

Ties every module above together into `RunLoopStateMachine`: a set of pure
functions from `(RunState, event, now)` to `(RunState, Decision)`. This is
the piece `application/runner.py` executes against real ports
ports — `domain/loop.py` itself performs no I/O; it only decides what I/O
should happen next.

```
Phase: PREFLIGHT → RUNNING → WAITING → PROBING → COMPLETE | FAILED
```

| Function | Called when | Key rule |
|---|---|---|
| `decide_preflight` | run starts | Mirrors `preflight_wait()` in the legacy script — check capacity before spending a real attempt. |
| `decide_after_turn` | a real turn completed | **A capacity rejection always outranks a completion claim** — even a `Done` verdict, because a limit message truncating mid-response could coincidentally contain marker-like text. Tested explicitly as `test_after_turn_limit_outranks_completion_claim`. |
| `decide_after_probe` | a throwaway probe turn completed while waiting | Re-classifies; `Available` resumes running, anything else reschedules. |

`Decision` is itself a closed union (`SendTurn | RunProbe | ScheduleProbe |
Finish`) so the executor in `application/` can pattern-match on exactly what
to do without the state machine reaching out and performing it directly.

## `forecast.py` — `Headroom`, `BurnRate`, `CapacityForecast`, `WindDownPolicy`, `WindDown`

Answers a question the capacity states in `capacity.py` deliberately don't:
not "am I blocked right now?" but "am I about to be blocked?" By the time a
real rejection arrives it's too late to hand off cleanly — the snapshot, the
stop summary, and the final save point all need capacity to *produce*, so
this module lets a run wind down while there's still room to do that
properly. Pure, and built around five testable laws:

```
F1  Unknown is never exhausted — a missing vendor field must not stop a run.
F2  Stale degrades to unknown, not to stale (past max_staleness).
F3  Never before the first completed turn (turns_spent >= 1).
F4  Monotone — lowering any headroom can never turn a wind-down back off.
F5  The binding dimension is the minimum *known* one, never the minimum
    including unknowns.
```

```python
@dataclass(frozen=True, slots=True)
class WindDownPolicy:
    enabled: bool = False
    headroom_floor: float = 0.15
    min_turns_reserve: int = 2
    max_staleness: timedelta = timedelta(minutes=15)

def forecast(available: Available, *, turns_spent: int, ..., now: datetime,
             policy: WindDownPolicy | None = None) -> CapacityForecast: ...

def should_wind_down(projection: CapacityForecast, policy: WindDownPolicy,
                      *, turns_spent: int) -> WindDown | None: ...
```

- `Headroom.fraction is None` means *unknown*, never `0.0` — conflating
  "we cannot see this dimension" with "there is none left" is exactly how a
  healthy run would get stopped for no reason (F1). `Headroom.staled()`
  implements F2: a reading older than `policy.max_staleness` reverts to
  unknown rather than being trusted indefinitely or treated as if it means
  zero headroom.
- `forecast()` takes `Available` specifically — not the whole `CapacityState`
  union — which is the enforcement mechanism for "vendor utilization is
  informational and must never itself block a turn": forecasting only ever
  runs once the vendor has already said the run isn't blocked, and it
  decides whether to stop *after* a turn completes, never whether to send
  one.
- Dimensions considered are vendor `utilization` (from `Available`) plus
  budget-derived `turns` and `dollars` headroom; budget caps never go stale
  since they're computed exactly from ledger state, not read off an event.
- `_binding()` implements F5: the tightest *known* dimension wins; if every
  dimension is unknown, the forecast itself is unknown and `should_wind_down`
  returns `None` regardless of policy (F1 again, at the decision layer).
- `should_wind_down()` requires `policy.enabled`, `turns_spent >= 1` (F3), and
  a known projection (F1) before checking any dimension; a `turns` dimension
  is deliberately skipped in the per-dimension floor check when
  `min_turns_reserve > 0` — that dimension is instead covered by the
  separate `turns_until_exhaustion <= min_turns_reserve` check, expressed in
  absolute turns rather than a fraction of the cap.
- `enabled` defaults to `False` on purpose: shipping a predictive stop with
  no real forecast data to tune it against would apply an unvalidated guess
  to every run, so the first release only measures. As of this writing,
  nothing in the CLI, environment variables, or config file ever constructs
  a `WindDownPolicy` with non-default values — see
  [configuration.md](../getting-started/configuration.md#predictive-wind-down-winddownpolicy).

## `control.py` — `ControlCommand` union and `stop_outranks()`

Operator mid-run control arrives as an inbox of commands rather than a single
mutable "current intent" flag — each command type is closed and validated in
its own `__post_init__`, so a malformed control-plane write (blank prompt
text, unknown permission mode, unknown resource kind) fails at parse time
instead of silently becoming a no-op turn boundary decision.

```python
ControlCommand = (
    StopCommand | WindDownCommand | PromptNowCommand | PromptDeferredCommand
    | SetModelCommand | SetEffortCommand | SetPresetCommand
    | SetPermissionModeCommand | SetCwdCommand | SlashCommand
    | ApproveToolCommand | DenyToolCommand | ResourceMutateCommand
    | ResponseFeedbackCommand | ResponseRetryCommand
)
```

- `StopCommand` is honoured immediately; `WindDownCommand` is deliberately
  weaker — it lets the in-flight turn finish so handoff artifacts describe a
  consistent point, and it also breaks an in-progress capacity wait so an
  operator doesn't have to wait out a rate-limit window just to rotate away.
- `PromptNowCommand` applies at the next operator boundary; `PromptDeferredCommand`
  waits for a natural break (after a `Continue` verdict, before the next send)
  — same shape, different urgency, modeled as distinct types rather than a
  boolean flag on one.
- `stop_outranks()` normalizes a batch of commands polled from the inbox in
  one pass: any `StopCommand` present collapses the whole batch to just
  `[StopCommand()]`; failing that, only the latest `WindDownCommand` survives.
  For every other kind, only the latest instance in the batch wins (last
  write wins per type), except `ApproveToolCommand` / `DenyToolCommand` /
  `ResourceMutateCommand`, which are all kept in original order since each is
  keyed by its own `request_id` / resource identity downstream.

## `handoff_marker.py` — `HandoffMarker`, `EXIT_WIND_DOWN`

The file a supervisor trusts to mean "this run's handoff is complete and
every artifact it names is really on disk." It's a separate file from a
status snapshot specifically because a snapshot is rewritten every turn and
so proves nothing about completeness — `handoff.json` is written exactly
once, only after every artifact it references already exists.

```python
@dataclass(frozen=True, slots=True)
class HandoffMarker:
    run_id: str
    reason: str
    produced_at: datetime
    headroom: float | None = None
    snapshot_path: str | None = None
    bundle_path: str | None = None
    stop_summary_path: str | None = None
    savepoint_ref: str | None = None
    session_id: str | None = None
    turns_spent: int = 0
    dollars_spent: float = 0.0
    remaining_work: tuple[str, ...] = ()
```

- `named_artifacts()` returns exactly the paths this marker claims exist —
  that's the contract a reader relies on. A process killed mid-wind-down
  simply never writes the marker at all, so a supervisor falls back to its
  pre-existing reactive path rather than ever seeing a half-written handoff.
- `parse_marker()` hard-fails on any `schema_version` other than the current
  one — no silent best-effort parsing of a future or unknown schema.
- `EXIT_WIND_DOWN = 75` is a deliberately chosen process exit code (0/1/2 and
  130 were already taken) so a supervisor can distinguish "handed off, resume
  me elsewhere" from an ordinary failure using the exit status alone.

## `model_profile.py` — `ModelAliases`, `ModelEffortProfile`

Indirection between the operator-facing vocabulary (`low`/`medium`/`high`
presets, `low`…`max` effort levels) and concrete Anthropic model ids, so a
preset name keeps meaning "the cheap one" even when the underlying model id
it maps to changes across releases.

```python
EffortLevel = Literal["low", "medium", "high", "xhigh", "max"]
PresetName = Literal["low", "medium", "high"]

@dataclass(frozen=True, slots=True)
class ModelEffortProfile:
    model: str
    effort: EffortLevel
    preset: PresetName | None = None
```

- `resolve_profile()` is the single entry point CLI/config inputs go through:
  a preset sets model+effort first, then an explicit `--model`/`--effort`
  overrides individually. Supplying a raw `--model` that doesn't match any
  alias clears the applied preset tag, since the profile is no longer one of
  the three named tiers.
- `escalate_profile()`/`downgrade_profile()` step through preset tiers first
  (`low → medium → high` / reverse) and only adjust `effort` once already at
  the top/bottom preset.

## `model_policy.py` — `decide_auto_model()`

Encodes when claudeloop should change its own model/effort profile mid-run
without a human watching, and — just as importantly — when it must not, so
automatic escalation can never fight an operator's explicit choice.

```python
def decide_auto_model(
    current: ModelEffortProfile,
    *,
    consecutive_no_progress: int,
    consecutive_progress: int,
    blocked: bool,
    dollars_spent: float,
    max_dollars: float | None,
    budget_downgrade_done: bool,
    operator_locked: bool,
    auto_enabled: bool,
) -> AutoModelDecision: ...
```

- `operator_locked` or `not auto_enabled` short-circuits to no change before
  any other rule runs — an operator's explicit model/preset command always
  wins over the automatic policy.
- Escalation (`blocked` or two consecutive no-progress turns) is checked
  first and **outranks every downgrade path** in the same decision.
- A one-time budget-forced downgrade to the `low` preset fires when spend
  crosses 80% of `max_dollars`, but still loses to an escalate condition in
  the same call. Ordinary downgrade-on-progress is checked last.

## `permission.py` — permission-mode translation

A pure lookup table between the names an operator types (`bypass`, `manual`,
`accept-edits`, `plan`, `auto`) and the literal strings the Claude Agent
SDK's `permission_mode` expects (`bypassPermissions`, `default`,
`acceptEdits`, `plan`, `auto`, `dontAsk`) — an explicit two-way mapping
rather than a naming convention, so a typo fails validation instead of
silently reaching the SDK as a different mode than intended.

```python
UserPermissionMode = Literal["bypass", "manual", "accept-edits", "plan", "auto"]
SdkPermissionMode = Literal["bypassPermissions", "default", "acceptEdits", "plan", "auto", "dontAsk"]
```

- `parse_user_permission_mode()` normalizes case/underscore-vs-hyphen
  variants before validating, so both SDK-style and user-style spellings of
  the same mode are accepted.
- The SDK's `dontAsk` mode has no distinct user-facing name — it maps back to
  `manual`, an intentional many-to-one collapse.
- The default user permission mode is `bypass` — claudeloop starts
  bypass-capable since it must never block on a human to grant tool
  permission.

## `savepoint.py` — `SavePointRef`, `UnwindResult`

Value objects for a git-backed "save point" — a numbered, labeled checkpoint
of the worktree taken between turns so a run can be rewound without losing
the audit trail of what changed and when.

```python
@dataclass(frozen=True, slots=True)
class SavePointRef:
    n: int
    ref: str
    sha: str
    label: str
    at: datetime
    committed: bool = False

@dataclass(frozen=True, slots=True)
class UnwindResult:
    to: SavePointRef
    backup_ref: str | None
    restored_sha: str
```

- `__post_init__` enforces `n >= 1` and non-blank `ref`/`sha` — a save point
  reference is meaningless without a real commit identity behind it.
- `committed` distinguishes "created a new commit" from "the tree was
  unchanged, so the ref just points at the prior commit."
- `UnwindResult.backup_ref` is optional: rewinding may or may not leave a
  recovery ref behind depending on whether the pre-unwind state itself
  needed preserving.

## `savepoint_message.py` — `format_savepoint_commit_message()`

Pure formatting of the Conventional-Commits-style subject/body claudeloop
writes for each savepoint commit, kept separate from the git plumbing itself
so the message format is unit-testable without a real repository.

- Subject format is `chore(claudeloop): turn {n} — {headline}`, truncated at
  72 characters to respect conventional git subject-line length.
- The headline is chosen by preference order: first non-blank line of the
  turn's summary, then the basename of the first changed path, then a fixed
  fallback — so a savepoint always gets a human-scannable subject even when
  the model produced no summary text.
- The body always renders all sections (`Summary`, `Remaining work`,
  `Changed paths`) with an explicit `(none)` placeholder rather than
  omitting empty sections, so the commit body shape is stable regardless of
  what the turn actually produced.

## `slash.py` — `ParsedSlash`, slash-command allowlist

Validates operator-injected slash commands against a fixed allowlist before
they're turned into a prompt — the allowlist exists specifically so a slash
command is never executed as a shell command or passed through unchecked;
only names claudeloop recognizes make it to the model at all.

```python
ALLOWED_SLASH_COMMANDS = frozenset({
    "help", "clear", "compact", "cost", "doctor", "memory", "model",
    "permissions", "plan", "review", "status", "config", "vim",
    "terminal-setup", "claudeloop-status", "claudeloop-savepoint",
})
```

- `parse_slash()` requires a leading `/`, a non-blank command name, and
  membership in `ALLOWED_SLASH_COMMANDS` (case-insensitive) — anything else
  raises rather than being forwarded.
- `slash_to_prompt()` is the only place a validated slash command becomes
  actual prompt text — the allowlist check always runs first.
- The allowlist mixes real Claude Code slash commands with two
  claudeloop-specific extensions (`claudeloop-status`, `claudeloop-savepoint`).

## `snapshot.py` — `SnapshotRef`, snapshot reasons

Defines what a run "snapshot" is a pointer to, and which snapshot reasons are
serious enough to be immutable and bundled into a handoff — a `status`
snapshot (informational, taken often) is treated completely differently from
a `finished`/`failed`/`handoff` snapshot (must be complete and never
overwritten).

```python
SnapshotReason = Literal[
    "started", "stopped", "finished", "failed", "waiting", "status", "manual", "handoff",
]
```

- `canonical_json_bytes()`/`digest_payload()` produce a stable
  (sorted-keys, no-whitespace) SHA-256 digest of a snapshot payload,
  independent of dict key ordering or datetime repr differences between
  runs.
- `"handoff"` is deliberately included among the bundled reasons even though
  the run isn't finished: a handoff snapshot is the successor's *only*
  record of what happened, so it must bundle completely just like a
  genuinely terminal reason.
- `parse_snapshot_reason()` is a strict allowlist parser — no reason string
  reaches storage without being one of the named cases.

## `stop_summary.py` — `StopSummaryInput`, `render_stop_summary()`

Pure Markdown assembly for the human-readable summary claudeloop writes when
a run stops mid-work — a pure function over an explicit input dataclass
(rather than formatting scattered across the run loop) so the document's
shape is independently testable and stable regardless of which code path
triggered the stop.

- Every section renders unconditionally with an explicit fallback string
  rather than being omitted when empty — a reader should never wonder
  whether a missing section means "nothing to report" or "the writer
  forgot."
- Distinguishes `remaining_plan_items` (the plan file's own checkbox
  checklist) from `remaining_work` (the last turn's structured verdict) as
  two separate rendered sections, because they can legitimately disagree.
- Always includes the exact `claudeloop logs --run-id {run_id} --follow`
  command and the raw events path, so the summary is self-contained enough
  to hand to a different operator with no other context.

## `verbosity.py` — `Verbosity`, `LogPlan`, `resolve_log_plan()`

Resolves `-v`/`--quiet`/`--log-level` CLI flags into a single logging
intent, kept in `domain/` specifically so "what `-vv` means" is one decision
that's identical across every entry point rather than something each runner
re-derives.

```python
class Verbosity(IntEnum):
    QUIET = -1
    NORMAL = 0
    VERBOSE = 1
    TRACE = 2
    FIREHOSE = 3
```

- `QUIET` and `NORMAL` differ only by log *level*; the tiers above `VERBOSE`
  differ by *scope* instead — `TRACE` widens to third-party library logs,
  `FIREHOSE` further includes full payloads.
- `parse_verbosity()` rejects `--quiet` combined with any `--verbose` count
  as mutually exclusive, and clamps an oversized `-vvvv...` count down to
  `FIREHOSE` rather than erroring.
- An explicit `--log-level` always wins over the `-v` count for the log
  level itself, but the count still independently widens third-party/payload
  scope — so `--log-level WARNING -vvv` is a valid way to ask for warnings
  from everything, not a contradiction.

## `chatter.py` — `TruncatedText`, chatter event payloads

Bounds how much raw model/tool "chatter" text claudeloop will ever put into
an event payload or log line, so a single oversized turn can't blow up
memory or storage for an unattended, potentially multi-day run.

- `truncate_chatter()` cuts on a UTF-8 boundary rather than a raw byte
  offset, so the result is never an invalid, mid-codepoint UTF-8 string.
- `chatter_event_payload()` returns `None` outright in `"off"` mode — the
  caller's event emission is expected to skip the event entirely rather
  than emit an empty payload.
- In `"summary"` mode, the payload still includes the full truncated text
  alongside a much shorter preview — the preview is for compact console
  logs, but stream-UI/event consumers reading the same payload are never
  capped down to preview size.

## Design principles this module holds itself to

1. **Every public type is a frozen dataclass or a closed union of them.**
   No mutation, no inheritance hierarchies standing in for sum types.
2. **No third-party imports, ever.** `domain/` imports only `dataclasses`,
   `datetime`, `enum`, `typing`, and its own siblings. This is enforced by
   `import-linter`, not just convention.
3. **Every branch is a tested branch.** The domain package carries a 100%
   coverage floor in CI specifically because untested branches here are the
   most consequential kind of bug — they're the code that decides whether an
   unattended, multi-day run keeps going, waits, or gives up.
4. **Hypothesis property tests, not just examples**, for anything with a
   numeric or time-based invariant (`waiting.py`'s backoff and clamping).
   Property tests are what caught the `timedelta` overflow bug during
   development — an example-based test at any specific `probe_count` would
   have passed right up until it didn't in production.
