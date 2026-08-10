# autoclaude

[![PyPI](https://img.shields.io/pypi/v/autoclaude)](https://pypi.org/project/autoclaude/)
[![Python versions](https://img.shields.io/pypi/pyversions/autoclaude)](https://pypi.org/project/autoclaude/)
[![CI](https://github.com/adammatthewsteinberger/autoclaude/actions/workflows/ci.yml/badge.svg)](https://github.com/adammatthewsteinberger/autoclaude/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Onion-architected, autonomous Claude Code session runner and full Anthropic
SDK CLI** — never blocks on a human, distinguishes an exhausted rate-limit
window from exhausted credits, and resumes safely across usage windows.

> **Not affiliated with `autoclaude-cli`.** There is a separate, unrelated
> PyPI package named `autoclaude-cli` (`github.com/grezy-software/autoclaude-cli`)
> in a similar problem space. **This project is `autoclaude`** (no `-cli`
> suffix), published by [`adammatthewsteinberger`](https://github.com/adammatthewsteinberger).
> The two share no code and are not connected.

## What problem this solves

Claude Code sessions hit usage limits. A `claude -p` invocation ending
doesn't tell you whether the *task* finished or just that *turn* did. And
when a rate limit rejects you, you can't tell from the outside whether
waiting will ever help — a five-hour window resets on its own; an exhausted
credits balance never will, no matter how long you wait.

`autoclaude` exists to get all three of those distinctions right,
automatically, so you can hand it a plan and walk away — including handling
the case where you top up your account's credits while it's mid-wait, which
it notices on the next probe rather than at some fixed deadline.

This project began as [`legacy/claude_autoresume.py`](legacy/claude_autoresume.py),
a single-file script that did this by shelling out to `claude -p` and
regex-scraping its output. `autoclaude` replaces that with a tested,
typed, onion-architected package built on the official `claude-agent-sdk`.
See [`docs/architecture/decisions/`](docs/architecture/decisions/) for why
each specific change was made.

## Install

```bash
pipx install autoclaude
```

See [`docs/getting-started/installation.md`](docs/getting-started/installation.md)
for requirements and a from-source setup.

## Quickstart

```bash
autoclaude run handoff.md      # seed a session from a plan file and run to completion
autoclaude resume               # resume whatever you were last working on
autoclaude resume --session-id <id>
autoclaude doctor                # pre-flight checks before a long unattended run
```

Full walkthrough: [`docs/getting-started/quickstart.md`](docs/getting-started/quickstart.md).

## Why it's different from just retrying on 429

| | Naive retry | `autoclaude` |
|---|---|---|
| Sees an HTTP 429 | Sleeps a fixed duration, retries | Classifies *why* — a waitable rate-limit window, or exhausted credits that only a human can fix |
| Credits exhausted | Sleeps forever, no reset time exists | Probes on a bounded backoff and tells you it needs you |
| A credit top-up arrives mid-wait | Not noticed until the fixed sleep ends | Noticed on the next scheduled probe |
| Turn ends vs. task ends | No structured signal — a marker string, easily confused with a truncated limit message | Structured per-turn JSON verdict, with the legacy marker kept only as a fallback |
| Asked a clarifying question | Hangs waiting for stdin, or fabricates an answer | Denies the tool call with guidance, so the model proceeds on a stated, auditable assumption |

See [`docs/guides/rate-limits-and-credits.md`](docs/guides/rate-limits-and-credits.md)
and [`docs/guides/never-blocking.md`](docs/guides/never-blocking.md) for the
full reasoning.

## Documentation

Full docs (built with MkDocs Material) live at
**https://adammatthewsteinberger.github.io/autoclaude/**, and are also
readable directly under [`docs/`](docs/) in this repo:

| | |
|---|---|
| [Getting started](docs/getting-started/) | Install, quickstart, configuration |
| [Guides](docs/guides/) | How autonomous runs work, rate limits vs. credits, never blocking, completion detection |
| [Architecture](docs/architecture/overview.md) | The onion layers, the domain model, the run-loop state machine |
| [Decision records](docs/architecture/decisions/) | Why each hard call was made |
| [Contributing](docs/contributing/) | Development setup, testing philosophy, release process |
| [Plans](docs/plans/) | The original approved plans this project was built from |

## Project status

Pre-1.0. Milestone **M1 (the pure domain core)** is complete: a fully tested
set of value objects and a pure state machine modeling every hard decision
the runner makes (rate-limit classification, adaptive waiting, completion
detection, budget tracking). Milestones **M2–M5** — the actual agent
integration, the CLI, the generated REST surface, and final polish — are
roadmap. See [`docs/plans/architecture-and-roadmap.md`](docs/plans/architecture-and-roadmap.md).

## Contributing

Contributions are welcome — see [`CONTRIBUTING.md`](CONTRIBUTING.md) for the
gitflow branch model, Conventional Commits requirement, and how to run every
quality gate locally. This repo also ships a set of
[Claude Code skills](.claude/skills/) that make Claude itself an effective
contributor to this specific codebase — see [`CLAUDE.md`](CLAUDE.md).

## Security

This tool bypasses Claude Code's interactive permission prompts by design
(that's what makes autonomous operation possible) and handles API
credentials. See [`SECURITY.md`](SECURITY.md) for the threat model and how
to report a vulnerability.

## License

MIT — see [`LICENSE`](LICENSE).
