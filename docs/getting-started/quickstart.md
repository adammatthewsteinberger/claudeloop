# Quickstart

!!! note "Roadmap"
    The commands below describe the intended M2 CLI surface — the runner
    itself isn't wired up yet (see
    [project status](installation.md#project-status)). This page will be
    updated to match as milestones land; until then, treat it as the target
    UX the domain layer already implements the decision logic for.

## Run a plan file to completion, unattended

```bash
autoclaude run handoff.md
```

Seeds a brand-new Claude Code session with the contents of `handoff.md`, then
keeps resuming it — across turns, across rate-limit windows, across a
credits top-up — until the task reports itself genuinely complete. Run this
from whatever directory you want Claude Code to operate in; that's the
directory the session and any file edits happen in.

## Resume a specific session

```bash
autoclaude resume --session-id <id>
```

## Resume whatever you were last working on

```bash
autoclaude resume
```

Auto-selects the most recently modified Claude Code session for the current
working directory (via the SDK's `list_sessions()`, not by parsing
transcript files directly) and prints exactly which one it picked — session
id, last-activity time, git branch, first-prompt preview — before doing
anything, so you can interrupt it if it guessed wrong.

## See what's running or waiting

```bash
autoclaude sessions
```

## Check your setup before starting a long unattended run

```bash
autoclaude doctor
```

Verifies Claude Code is installed and authenticated, checks any configured
MCP servers up front (since MCP OAuth can't complete unattended — see
[`../architecture/decisions/0007-ask-user-question-denied-with-guidance.md`](../architecture/decisions/0007-ask-user-question-denied-with-guidance.md)),
and confirms the working directory is safe to bypass permissions in.

## Configuration

`autoclaude` reads configuration in this precedence order (highest wins):

1. Command-line flags (`--max-wait`, `--max-turns`, `--log-level`, ...)
2. Environment variables (`AUTOCLAUDE_*`)
3. A config file (`autoclaude.toml` in the working directory, or
   `~/.config/autoclaude/config.toml`)
4. Built-in defaults

See [`../guides/never-blocking.md`](../guides/never-blocking.md) and
[`../guides/rate-limits-and-credits.md`](../guides/rate-limits-and-credits.md)
for what each of the safety-relevant settings actually controls.
