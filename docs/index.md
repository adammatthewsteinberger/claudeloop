# autoclaude

**Onion-architected, autonomous Claude Code session runner and full Anthropic
SDK CLI** — never blocks on a human, distinguishes an exhausted rate-limit
window from exhausted credits, and resumes safely across usage windows.

!!! info "Not affiliated with `autoclaude-cli`"
    There is a separate, unrelated PyPI package named `autoclaude-cli`
    (`github.com/grezy-software/autoclaude-cli`) in a similar problem space.
    **This project is `autoclaude`** (no `-cli` suffix), published by
    `adammatthewsteinberger`. The two are not affiliated and share no code.

## What problem this solves

Claude Code sessions hit usage limits. A `claude -p` invocation ending
doesn't tell you whether the *task* finished or just that *turn* did. And
when a rate limit rejects you, you can't tell from the outside whether
waiting will ever help — a five-hour window will reset on its own; an
exhausted credits balance never will, no matter how long you wait.

`autoclaude` exists to get all three of those distinctions right,
automatically, so you can hand it a plan and walk away — including handling
the case where you top up your account's credits while it's mid-wait.

## Where to go next

| I want to... | Read |
|---|---|
| Install it and run my first autonomous session | [Getting started](getting-started/installation.md) |
| Understand how rate limits and credits are told apart | [Rate limits vs. credits](guides/rate-limits-and-credits.md) |
| Understand why it can never get stuck waiting on me | [Never blocking](guides/never-blocking.md) |
| See the full system design | [Architecture overview](architecture/overview.md) |
| See *why* a specific hard call was made | [Architecture decision records](architecture/decisions/0001-onion-architecture-with-import-linter.md) |
| Contribute code | [Development guide](contributing/development.md) |
| See the original plans this project was built from | [Plans](plans/architecture-and-roadmap.md) |

## Project status

Pre-1.0. Milestone **M1 (the pure domain core)** is complete — a fully
tested set of value objects and a pure state machine that model every hard
decision the runner makes. Milestones **M2–M5** (the actual agent
integration, the CLI, the generated REST surface, and final polish) are
roadmap. See [`plans/architecture-and-roadmap.md`](plans/architecture-and-roadmap.md)
for the build order.

## License

MIT. See [LICENSE](https://github.com/adammatthewsteinberger/autoclaude/blob/main/LICENSE).
