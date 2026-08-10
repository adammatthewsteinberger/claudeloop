from __future__ import annotations

import re

from typer.testing import CliRunner, Result

from claudeloop import __version__
from claudeloop.cli.app import app

runner = CliRunner()

# Rich (via Typer) styles each hyphen in option names separately when color is
# on — `--session-id` becomes `\x1b[1m-\x1b[0m\x1b[1m-session\x1b[0m...` — so
# substring asserts against raw stdout flake on color-capable CI runners.
# Force a dumb, colorless terminal for every invoke in this module.
_NO_COLOR_ENV = {"NO_COLOR": "1", "TERM": "dumb", "FORCE_COLOR": "0"}
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def _invoke(*args: str) -> Result:
    return runner.invoke(app, list(args), env=_NO_COLOR_ENV)


def _plain(text: str) -> str:
    return _ANSI_ESCAPE.sub("", text)


def test_version_flag() -> None:
    result = _invoke("--version")
    assert result.exit_code == 0
    assert __version__ in _plain(result.stdout)


def test_help_flag_lists_all_commands() -> None:
    result = _invoke("--help")
    assert result.exit_code == 0
    stdout = _plain(result.stdout)
    for command in ("run", "resume", "sessions", "doctor"):
        assert command in stdout


def test_no_args_shows_help_rather_than_a_traceback() -> None:
    # no_args_is_help=True in cli/app.py: Click's test runner deliberately
    # raises SystemExit(2) for this case (its own bookkeeping for "no
    # subcommand given"), distinct from an unhandled application exception —
    # what actually matters is that help rendered, not a stack trace.
    result = _invoke()
    assert isinstance(result.exception, SystemExit)
    assert "Usage:" in _plain(result.output)


def test_run_requires_an_existing_plan_file() -> None:
    result = _invoke("run", "/does/not/exist.md")
    assert result.exit_code != 0


def test_run_help() -> None:
    result = _invoke("run", "--help")
    assert result.exit_code == 0
    assert "PLAN_FILE" in _plain(result.stdout)


def test_resume_help() -> None:
    result = _invoke("resume", "--help")
    assert result.exit_code == 0
    assert "--session-id" in _plain(result.stdout)


def test_sessions_help() -> None:
    result = _invoke("sessions", "--help")
    assert result.exit_code == 0


def test_doctor_help() -> None:
    result = _invoke("doctor", "--help")
    assert result.exit_code == 0
