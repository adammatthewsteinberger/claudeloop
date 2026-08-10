# CLI reference

`src/claudeloop/cli/app.py` is the real Typer root; every command below
works today. This page is hand-maintained rather than auto-generated for
now — a `mkdocs-typer`-style auto-generated version is a reasonable future
improvement, but isn't in place yet.

## Command tree

```
claudeloop --version              Show the installed version and exit
claudeloop --help                 Manual-page style overview (NAME, SYNOPSIS, …)
claudeloop --man                  Same as --help
claudeloop run <plan-file>        Seed a fresh session from a markdown plan and run to completion
                                   [--max-turns] [--max-dollars] [--max-wait]
                                   [--log-level] [--log-file]
claudeloop resume [--session-id]  Resume a specific session, or auto-select the most recently
                                   modified one for the current directory
                                   [--max-turns] [--max-dollars] [--log-level] [--log-file]
claudeloop sessions [--cwd]       List known sessions, read-only
claudeloop doctor                 Pre-flight checks: claude CLI present, authentication,
                                   configured MCP servers, anthropic SDK, api surface, cwd safety
claudeloop api ...                 Generated 1:1 Anthropic SDK REST commands; see
                                   guides/rest-api-surface.md
```

See [`../getting-started/quickstart.md`](../getting-started/quickstart.md)
for worked examples of each, and
[`../getting-started/configuration.md`](../getting-started/configuration.md)
for every flag and its environment-variable equivalent.

## Exit codes

`run` and `resume` exit `0` on a genuinely completed task and non-zero on
any other outcome (a limit exceeded `--max-wait`, an authentication failure,
a `Blocked` verdict, budget exhaustion) — see
[`../architecture/run-loop-state-machine.md`](../architecture/run-loop-state-machine.md#states)
for the full list of terminal states and what each one means. `doctor`
exits `0` only if every check passes.
