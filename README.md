# claudeloop

[![PyPI](https://img.shields.io/pypi/v/claudeloop)](https://pypi.org/project/claudeloop/)
[![Python versions](https://img.shields.io/pypi/pyversions/claudeloop)](https://pypi.org/project/claudeloop/)
[![CI](https://github.com/adammatthewsteinberger/claudeloop/actions/workflows/ci.yml/badge.svg)](https://github.com/adammatthewsteinberger/claudeloop/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/adammatthewsteinberger/claudeloop/blob/main/LICENSE)

**Onion-architected, autonomous Claude Code session runner and full Anthropic
SDK CLI** — never blocks on a human, distinguishes an exhausted rate-limit
window from exhausted credits, and resumes safely across usage windows.

## What problem this solves

Claude Code sessions hit usage limits. A `claude -p` invocation ending
doesn't tell you whether the *task* finished or just that *turn* did. And
when a rate limit rejects you, you can't tell from the outside whether
waiting will ever help — a five-hour window resets on its own; an exhausted
credits balance never will, no matter how long you wait.

`claudeloop` exists to get all three of those distinctions right,
automatically, so you can hand it a plan and walk away — including handling
the case where you top up your account's credits while it's mid-wait, which
it notices on the next probe rather than at some fixed deadline.

This project began as [`legacy/claude_autoresume.py`](https://github.com/adammatthewsteinberger/claudeloop/blob/main/legacy/claude_autoresume.py),
a single-file script that did this by shelling out to `claude -p` and
regex-scraping its output. `claudeloop` replaces that with a tested,
typed, onion-architected package built on the official `claude-agent-sdk`.
See the [architecture decision records](https://adammatthewsteinberger.github.io/claudeloop/architecture/decisions/0001-onion-architecture-with-import-linter/) for why
each specific change was made.

## Install

```bash
pipx install claudeloop
```

See the [installation guide](https://adammatthewsteinberger.github.io/claudeloop/getting-started/installation/)
for requirements and a from-source setup.

## Quickstart

```bash
claudeloop run handoff.md      # seed a session from a plan file and run to completion
claudeloop resume               # resume whatever you were last working on
claudeloop resume --session-id <id>
claudeloop doctor                # pre-flight checks before a long unattended run
claudeloop api models list       # any Anthropic SDK endpoint (generated; see docs)
```

Full walkthrough: [quickstart](https://adammatthewsteinberger.github.io/claudeloop/getting-started/quickstart/).

## Why it's different from just retrying on 429

| | Naive retry | `claudeloop` |
|---|---|---|
| Sees an HTTP 429 | Sleeps a fixed duration, retries | Classifies *why* — a waitable rate-limit window, or exhausted credits that only a human can fix |
| Credits exhausted | Sleeps forever, no reset time exists | Probes on a bounded backoff and tells you it needs you |
| A credit top-up arrives mid-wait | Not noticed until the fixed sleep ends | Noticed on the next scheduled probe |
| Turn ends vs. task ends | No structured signal — a marker string, easily confused with a truncated limit message | Structured per-turn JSON verdict, with the legacy marker kept only as a fallback |
| Asked a clarifying question | Hangs waiting for stdin, or fabricates an answer | Denies the tool call with guidance, so the model proceeds on a stated, auditable assumption |

See [rate limits vs. credits](https://adammatthewsteinberger.github.io/claudeloop/guides/rate-limits-and-credits/)
and [never blocking on a human](https://adammatthewsteinberger.github.io/claudeloop/guides/never-blocking/) for the
full reasoning.

## Documentation

Full docs (built with MkDocs Material) live at
**https://adammatthewsteinberger.github.io/claudeloop/**. The same content
is in the [`docs/`](https://github.com/adammatthewsteinberger/claudeloop/tree/main/docs) directory on GitHub.

| | |
|---|---|
| [Getting started](https://adammatthewsteinberger.github.io/claudeloop/getting-started/installation/) | Install, quickstart, configuration |
| [Guides](https://adammatthewsteinberger.github.io/claudeloop/guides/autonomous-runs/) | How autonomous runs work, rate limits vs. credits, never blocking, completion detection |
| [Architecture](https://adammatthewsteinberger.github.io/claudeloop/architecture/overview/) | The onion layers, the domain model, the run-loop state machine |
| [Decision records](https://adammatthewsteinberger.github.io/claudeloop/architecture/decisions/0001-onion-architecture-with-import-linter/) | Why each hard call was made |
| [Contributing](https://adammatthewsteinberger.github.io/claudeloop/contributing/development/) | Development setup, testing philosophy, release process |
| [Plans](https://adammatthewsteinberger.github.io/claudeloop/plans/architecture-and-roadmap/) | The original approved plans this project was built from |

## Project status

Pre-1.0, but functional through milestone **M5**. The CLI above genuinely
works — `run`/`resume` drive Claude Code through `claude-agent-sdk`,
`sessions` and `doctor` run against your environment, and **`claudeloop api`**
exposes a generated 1:1 Anthropic SDK REST surface with a CI drift gate.
`domain`/`application` carry a CI-enforced 100% test-coverage gate, with a
live test suite (`tests/live/`) exercising the installed console script.
See the [architecture roadmap](https://adammatthewsteinberger.github.io/claudeloop/plans/architecture-and-roadmap/).

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](https://github.com/adammatthewsteinberger/claudeloop/blob/main/CONTRIBUTING.md) for the
gitflow branch model, Conventional Commits requirement, and how to run every
quality gate locally. This repo also ships a set of
[Claude Code skills](https://github.com/adammatthewsteinberger/claudeloop/tree/main/.claude/skills/) that make Claude itself an effective
contributor to this specific codebase — see [CLAUDE.md](https://github.com/adammatthewsteinberger/claudeloop/blob/main/CLAUDE.md).

## Security

This tool bypasses Claude Code's interactive permission prompts by design
(that's what makes autonomous operation possible) and handles API
credentials. See [SECURITY.md](https://github.com/adammatthewsteinberger/claudeloop/blob/main/SECURITY.md) for the threat model and how
to report a vulnerability.

## License

MIT — see [LICENSE](https://github.com/adammatthewsteinberger/claudeloop/blob/main/LICENSE).
