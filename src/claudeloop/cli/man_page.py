"""Manual-page style help for the root ``claudeloop`` command.

PyPI users and packagers often expect ``--help`` to read like ``man 1`` output.
Subcommands keep Typer's usual ``--help`` (option details); only the top-level
invocation uses this document.
"""

from __future__ import annotations

from claudeloop import __version__

_DOCS = "https://adammatthewsteinberger.github.io/claudeloop/"
_REPO = "https://github.com/adammatthewsteinberger/claudeloop"


def render_man_page() -> str:
    """Return a plain-text manual page (suitable for ``man -l -``)."""
    return f"""\
CLAUDELOOP(1)                         User Commands                         CLAUDELOOP(1)

NAME
       claudeloop - autonomous Claude Code session runner and Anthropic SDK CLI

SYNOPSIS
       claudeloop [--help | -h] [--version]
       claudeloop run [OPTIONS] PLAN_FILE
       claudeloop resume [OPTIONS]
       claudeloop sessions [--cwd PATH]
       claudeloop doctor
       claudeloop api [OPTIONS] COMMAND [ARGS]...

DESCRIPTION
       claudeloop drives Claude Code sessions to completion without blocking on
       a human: it classifies rate-limit rejections, waits only when a window
       reset is knowable, probes when credits may return, and resumes across
       turns.  It also exposes a generated 1:1 command tree over the anthropic
       Python SDK as claudeloop api.

       Run claudeloop doctor before long unattended runs.

COMMANDS
       run PLAN_FILE
              Start a new session from a markdown plan file and run until the
              task completes or a terminal limit is hit.

       resume [--session-id ID]
              Continue an existing session.  Without --session-id, selects the
              most recently modified session for the current working directory
              and prints which session was chosen.

       sessions [--cwd PATH]
              List known Claude Code sessions (read-only).

       doctor
              Pre-flight checks: Claude CLI, authentication, MCP servers,
              anthropic SDK import, and api surface wiring.

       api
              Generated REST/SDK commands (e.g. claudeloop api models list).
              Use claudeloop api --help and claudeloop api <resource> --help
              for endpoint-specific options.

OPTIONS
       --help, -h
              Display this manual page and exit.

       --version
              Print the installed claudeloop version and exit.

       Subcommand options
              Each of run, resume, sessions, doctor, and api accepts --help
              with Typer-style option listings.  Common run/resume flags include
              --max-turns, --max-dollars, --max-wait (run only), --model,
              --log-level, and --log-file.  Configuration also loads from
              claudeloop.toml and CLAUDELOOP_* environment variables.

EXIT STATUS
       0      Success (run/resume finished with a Done verdict; doctor passed
              every check).

       1      Failure (run/resume blocked or exhausted limits; doctor reported
              a failed check; invalid arguments).

ENVIRONMENT
       ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN
              Credentials for the Anthropic API (also used indirectly via the
              Claude Code CLI).

       CLAUDELOOP_*
              Override runner settings (see configuration guide on the web).

FILES
       claudeloop.toml
              Optional per-project configuration in the working directory.

       ~/.config/claudeloop/config.toml
              Optional user configuration.

       claudeloop.log.jsonl
              Default JSONL audit log path when --log-file is not set.

SEE ALSO
       Full documentation: {_DOCS}
       Repository: {_REPO}
       claudeloop run --help, claudeloop resume --help, claudeloop api --help

VERSION
       claudeloop {__version__}

CLAUDELOOP(1)                         User Commands                         CLAUDELOOP(1)
"""


def write_man_page() -> None:
    import sys

    text = render_man_page()
    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")
