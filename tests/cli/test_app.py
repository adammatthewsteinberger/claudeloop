from __future__ import annotations

from typer.testing import CliRunner

from claudeloop import __version__
from claudeloop.cli.app import app

runner = CliRunner()


def test_version_flag() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_help_flag_lists_all_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("run", "resume", "sessions", "doctor"):
        assert command in result.stdout


def test_no_args_shows_help_rather_than_a_traceback() -> None:
    # no_args_is_help=True in cli/app.py: Click's test runner deliberately
    # raises SystemExit(2) for this case (its own bookkeeping for "no
    # subcommand given"), distinct from an unhandled application exception —
    # what actually matters is that help rendered, not a stack trace.
    result = runner.invoke(app, [])
    assert isinstance(result.exception, SystemExit)
    assert "Usage:" in result.output


def test_run_requires_an_existing_plan_file() -> None:
    result = runner.invoke(app, ["run", "/does/not/exist.md"])
    assert result.exit_code != 0


def test_run_help() -> None:
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "PLAN_FILE" in result.stdout


def test_resume_help() -> None:
    result = runner.invoke(app, ["resume", "--help"])
    assert result.exit_code == 0
    assert "--session-id" in result.stdout


def test_sessions_help() -> None:
    result = runner.invoke(app, ["sessions", "--help"])
    assert result.exit_code == 0


def test_doctor_help() -> None:
    result = runner.invoke(app, ["doctor", "--help"])
    assert result.exit_code == 0
