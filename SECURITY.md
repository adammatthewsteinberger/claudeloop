# Security policy

## Why this matters more than usual for this project

`autoclaude` is designed to drive Claude Code **unattended, for potentially
multi-day runs**, which means it:

- Bypasses Claude Code's interactive permission prompts by design
  (`permission_mode="bypassPermissions"`) — that's what makes autonomous
  operation possible, but it means a misconfigured or compromised run has
  more latitude than an interactive session would.
- Reads and handles Anthropic API credentials (via the Claude Code CLI's own
  auth, and directly for the generated REST surface over `anthropic`).
- Writes detailed debug logs, including full raw event streams, which could
  contain sensitive content from your prompts, tool outputs, or credentials
  if a redaction gap exists.
- Runs against the current working directory with elevated trust — the
  entire point is that it edits files and runs commands without asking
  first.

Treat any report touching these areas as high priority.

## Supported versions

Only the latest released version on PyPI receives security fixes. This
project is pre-1.0; there is no long-term-support branch.

## Reporting a vulnerability

**Do not open a public GitHub issue for a security vulnerability.**

Report privately via one of:

1. [GitHub Security Advisories](https://github.com/adammatthewsteinberger/autoclaude/security/advisories/new)
   for this repository (preferred — supports coordinated disclosure).
2. Email **adam@matthewsteinberger.com** with a clear description, steps to
   reproduce, and the version affected.

## What to expect

- **Acknowledgment** within 5 business days.
- **An initial assessment** (severity, affected versions) within 10
  business days.
- **Coordinated disclosure**: a fix is prepared and released before public
  details are shared, unless the reporter and maintainer agree on a
  different timeline (e.g. the issue is already public elsewhere).

## Threat model, briefly

**In scope:**

- Any way `autoclaude` could be induced to bypass its own "never block on a
  human" safety design in a way that causes *harmful* unattended action
  (as opposed to simply failing) — e.g. a prompt-injection path from tool
  output back into a decision the runner treats as authoritative.
- Credential handling — logging, redaction, or storage of API keys,
  `authorization_token`s, `access_token`s, `refresh_token`s, or
  `client_secret`s in a way that leaks them (to logs, to disk, to a
  third party).
- Path traversal or command injection in anything derived from a plan file,
  session content, or CLI arguments — the project's explicit design goal is
  "no `shell=True` anywhere," and any path that reintroduces that class of
  risk is a real finding.
- Any way the generated REST surface (`autoclaude api ...`, once built)
  could execute an unintended request against a live Anthropic account —
  destructive actions (archiving agents/environments/vaults, deleting
  resources) executed without a clear, deliberate invocation.

**Out of scope:**

- Vulnerabilities in the Claude Code CLI or the `anthropic` /
  `claude-agent-sdk` packages themselves — report those to Anthropic
  directly.
- Issues requiring an attacker to already have arbitrary code execution on
  the machine running `autoclaude` (at that point, the OS has already been
  compromised).
- Missing rate-limiting on your own account's API usage — that's an
  Anthropic account/billing concern, not a vulnerability in this tool.
