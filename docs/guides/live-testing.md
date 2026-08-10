# Live testing against a real Claude account

`tests/live/` exercises the actual installed CLI and a real
`claude`/Claude Code environment — not fakes. It's opt-in and tiered so it
never runs by accident.

## Why this exists

Offline tests (`tests/domain`, `tests/application`, `tests/infrastructure`,
`tests/cli`) verify logic against fakes and typed SDK dataclasses. They
cannot catch a real API's actual shapes and timing — and in this project,
they didn't: live testing against a real account is what found that
`SDKSessionInfo.last_modified` is milliseconds (not seconds, as its type
alone suggests), that `claude mcp list` genuinely takes ~14 seconds against
a real server list, and that some real sessions have no resolvable working
directory at all. None of that is discoverable from a mock.

## Running it

**Free tier — no token spend, safe to run anytime:**

```bash
pytest -m live tests/live/test_free_tier.py
```

Covers: building the wheel and installing it into a clean venv, then running
`autoclaude --version`/`--help` from that install (the specific check that
would have caught the broken `[project.scripts]` entry point this project
shipped with before M2); `autoclaude doctor` against your real environment;
`autoclaude sessions` listing your real session store, read-only.

**Paid tier — spends real tokens/turns, requires an explicit flag:**

```bash
pytest -m "live and paid" --run-paid-live tests/live/
```

A plain `pytest -m live` (no `--run-paid-live`) skips every paid test with a
clear reason rather than running them — this is enforced in
`tests/live/conftest.py`, not just documented.

## Neither tier runs by accident

- The default `addopts` in `pyproject.toml` is `-m "not live"`, so a bare
  `pytest` and every CI job skip the whole `tests/live/` tree.
- Paid tests carry both the `live` and `paid` markers and are skipped unless
  `--run-paid-live` is explicitly passed, even when `-m live` is given.

## Isolation and cost control

- Every live test that touches a session runs in a fresh temporary git
  repository (the `sandbox_repo` fixture in `tests/live/conftest.py`) —
  never a real project directory. This is also what keeps any session
  `autoclaude` creates during a test easy to spot and namespaced away from
  real work.
- Paid tests are expected to pin the cheapest available model, set small
  `max_turns`/`max_budget_usd` caps, and use minimal prompts.
- `autoclaude doctor`'s subprocess calls to `claude` use a generous timeout
  (60–90s) rather than racing real, observed latency (`claude mcp list`
  against 37 configured servers took ~14s in testing) — a live test timing
  out is a false failure, not a safety property, so timeouts here are set
  for correctness, not speed.

## What isn't covered yet

Paid-tier tests for `autoclaude run`/`autoclaude resume` completing a real
plan end-to-end, and the never-block `AskUserQuestion` test described in
the original build plan, are not yet implemented — only the free tier
above is. See `docs/plans/foss-and-documentation-plan.md` Phase C for the
originally scoped full tier.
