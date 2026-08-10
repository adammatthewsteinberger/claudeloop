# CLI reference (planned)

!!! note "Roadmap"
    `src/autoclaude/cli/` is scaffolded but not yet implemented (milestone
    M2). Once the Typer app exists, this page becomes auto-generated from it
    (via `mkdocs-typer` or an equivalent) rather than hand-maintained.

## Planned command tree

```
autoclaude run <plan-file>       Seed a fresh session from a markdown plan and run to completion
autoclaude resume [--session-id] Resume a specific or auto-detected session
autoclaude sessions              List known sessions and their status
autoclaude doctor                Pre-flight checks: auth, MCP servers, working directory safety
autoclaude api ...                Generated 1:1 surface over the anthropic REST SDK — see
                                   guides/rest-api-surface.md
```

See [`../getting-started/quickstart.md`](../getting-started/quickstart.md)
for worked examples of each, and
[`../getting-started/configuration.md`](../getting-started/configuration.md)
for every flag and its environment-variable equivalent.
