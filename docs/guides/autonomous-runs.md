# How an autonomous run works, end to end

This walks through the full lifecycle of `claudeloop run handoff.md`,
tying together the pieces documented individually elsewhere.

## 1. Preflight

Before spending a single real turn, the runner checks whether it's already
mid-cooldown — for example if a prior manual session hit its limit right
before you started `claudeloop`. `domain.loop.decide_preflight` handles
this; see [`../architecture/run-loop-state-machine.md`](../architecture/run-loop-state-machine.md).

## 2. The first turn

For `claudeloop run handoff.md`, the plan file's contents seed a brand-new
Claude Code session (`domain.plan.WorkPlan.parse` turns any checkbox items
in it into tracked work). For `claudeloop resume`, a continuation prompt is
sent to the resolved session instead. Every prompt gets a runtime-appended
instruction establishing autonomous operation — see
[never-blocking.md](never-blocking.md).

## 3. Evaluating what happened

When a turn completes, two independent things are checked, and their order
matters:

1. **Capacity** — did this turn hit a rate limit or run out of credits? See
   [rate-limits-and-credits.md](rate-limits-and-credits.md).
2. **Completion** — does the model report the *whole task* done, not just
   this turn? See [completion-detection.md](completion-detection.md).

**A capacity rejection always outranks a completion claim.** A turn cut off
mid-response by a limit could coincidentally contain marker-like text; the
run loop checks capacity first and never trusts a "done" claim from a turn
that didn't actually complete cleanly.

## 4. If capacity is available and the task isn't done

Send another turn immediately — no cooldown, because this wasn't a limit,
just a turn boundary. This mirrors the legacy script's observation that a
single `claude -p` invocation can end because the *turn* ended, not because
the *task* did, and the two look identical from the outside without a
structured signal to tell them apart.

## 5. If capacity is exhausted

Enter the waiting policy described in
[rate-limits-and-credits.md](rate-limits-and-credits.md) — a scheduled probe
loop, never a blind sleep.

## 6. Terminal states

- **Complete** — the model reports the whole task genuinely done, and
  capacity was available on that turn. Exit 0.
- **Failed** — authentication failure (never retried), a `Blocked` verdict
  (the model reports it can't proceed — e.g. missing MCP credentials), the
  configured budget exhausted, or `--max-wait` exceeded while still waiting
  on capacity. Exit non-zero, with the reason recorded in the audit log.

## Everything is logged

Every raw event — not just the human-readable summary — is preserved to a
per-run JSONL audit file, carrying `run_id`, `attempt_no`, `session_id`, and
`event_type` on every record. Nothing is lost, matching the legacy script's
"nothing is lost" property for its own raw log file. See
[`../architecture/decisions/`](../architecture/decisions/) for the reasoning
behind each of the decisions summarized on this page.
