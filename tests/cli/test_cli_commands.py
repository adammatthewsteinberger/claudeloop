"""Tests for CLI command modules — operator control commands.

Tests the thin Typer wrappers around bootstrap_ops, ensuring correct argument
routing and error handling without needing a live run.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from claudeloop.cli.app import app

runner = CliRunner()
_ENV = {"NO_COLOR": "1", "TERM": "dumb", "FORCE_COLOR": "0"}


def _run_dir(tmp_path: Path):
    from claudeloop.infrastructure.rundir import RunDirectory, runs_root_for

    return RunDirectory.create(runs_root_for(tmp_path), cwd=tmp_path)


class TestStopCommand:
    def test_stop_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(app, ["stop", "--run-id", run_id], env=_ENV)
        assert result.exit_code == 0
        assert "Stop requested" in result.output

    def test_stop_no_run_found(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["stop", "--run-id", "nonexistent"], env=_ENV)
        assert result.exit_code == 1


class TestPromptCommand:
    def test_prompt_needs_now_or_at_break(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["prompt", "hello"], env=_ENV)
        assert result.exit_code == 2
        assert "Specify exactly one" in result.output

    def test_prompt_both_now_and_at_break(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["prompt", "hello", "--now", "--at-break"], env=_ENV,
        )
        assert result.exit_code == 2

    def test_prompt_now_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["prompt", "hello", "--now", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0
        assert "Enqueued" in result.output

    def test_prompt_at_break(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["prompt", "hello", "--at-break", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0


class TestModelCommand:
    def test_model_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(app, ["model", "high", "--run-id", run_id], env=_ENV)
        assert result.exit_code == 0
        assert "set_model" in result.output

    def test_model_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["model", "high", "--run-id", "x"], env=_ENV)
        assert result.exit_code == 1


class TestEffortCommand:
    def test_effort_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(app, ["effort", "max", "--run-id", run_id], env=_ENV)
        assert result.exit_code == 0
        assert "set_effort" in result.output


class TestPresetCommand:
    def test_preset_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(app, ["preset", "high", "--run-id", run_id], env=_ENV)
        assert result.exit_code == 0
        assert "set_preset" in result.output


class TestSlashCommand:
    def test_slash_without_prefix_fails(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["slash", "no-prefix"], env=_ENV)
        assert result.exit_code == 2
        assert "must start with '/'" in result.output

    def test_slash_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["slash", "/help", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0
        assert "slash" in result.output.lower()


class TestWindDownCommand:
    def test_wind_down_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["wind-down", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0
        assert "Wind-down requested" in result.output

    def test_wind_down_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["wind-down", "--run-id", "nope"], env=_ENV)
        assert result.exit_code == 1


class TestLogsCommand:
    def test_logs_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["logs", "--run-id", "missing"], env=_ENV)
        assert result.exit_code == 1


class TestStatusCommand:
    def test_status_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(app, ["status", "--run-id", run_id], env=_ENV)
        assert result.exit_code == 0

    def test_status_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["status", "--run-id", "nope"], env=_ENV)
        assert result.exit_code == 1


class TestResetCommand:
    def test_reset_without_yes_fails(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["reset"], env=_ENV)
        assert result.exit_code == 1

    def test_reset_with_yes(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _run_dir(tmp_path)
        result = runner.invoke(app, ["reset", "--yes"], env=_ENV)
        assert result.exit_code == 0
        assert "Removed" in result.output


class TestRunsCommand:
    def test_runs_no_runs(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["runs"], env=_ENV)
        assert result.exit_code == 0
        assert "No runs" in result.output

    def test_runs_with_runs(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(app, ["runs"], env=_ENV)
        assert result.exit_code == 0
        assert run_id in result.output


class TestSessionsCommand:
    def test_sessions_no_sessions(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["sessions"], env=_ENV)
        assert result.exit_code == 0


class TestSavepointsCommand:
    def test_savepoints_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["savepoints", "--run-id", "nope"], env=_ENV)
        assert result.exit_code == 1

    def test_savepoints_empty(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(app, ["savepoints", "--run-id", run_id], env=_ENV)
        assert result.exit_code == 0
        assert "No save points" in result.output


class TestUnwindCommand:
    def test_unwind_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["unwind", "--to", "1", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1


class TestChatCommands:
    def test_chat_list_empty(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["chat", "list"], env=_ENV)
        assert result.exit_code == 0
        assert "No chats" in result.output

    def test_chat_show(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["chat", "show", "test-session"], env=_ENV)
        assert result.exit_code == 0

    def test_chat_rename(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["chat", "rename", "s1", "new-name"], env=_ENV)
        assert result.exit_code == 0
        assert "Renamed" in result.output

    def test_chat_delete_missing(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["chat", "delete", "nonexistent"], env=_ENV)
        assert result.exit_code == 1

    def test_chat_pin_unpin(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["chat", "pin", "s1"], env=_ENV)
        assert result.exit_code == 0
        result = runner.invoke(app, ["chat", "unpin", "s1"], env=_ENV)
        assert result.exit_code == 0

    def test_chat_unread_read(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["chat", "unread", "s1"], env=_ENV)
        assert result.exit_code == 0
        result = runner.invoke(app, ["chat", "read", "s1"], env=_ENV)
        assert result.exit_code == 0

    def test_chat_project(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["chat", "project", "s1", "my-project"], env=_ENV,
        )
        assert result.exit_code == 0
        assert "project" in result.output.lower()


class TestConnectorCommands:
    def test_connector_add_url(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app,
            ["connector", "add", "myconn", "http://localhost", "--run-id", run_id],
            env=_ENV,
        )
        assert result.exit_code == 0

    def test_connector_add_invalid_json(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app,
            ["connector", "add", "myconn", "{bad", "--run-id", run_id],
            env=_ENV,
        )
        assert result.exit_code == 2

    def test_connector_rm(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app,
            ["connector", "rm", "myconn", "--run-id", run_id],
            env=_ENV,
        )
        assert result.exit_code == 0

    def test_connector_list_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["connector", "list", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1


class TestToolCommands:
    def test_tool_approve_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["tool", "approve", "req-1", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1

    def test_tool_deny_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["tool", "deny", "req-1", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1


class TestWatchCommand:
    def test_watch_sys_stdout_isatty(self) -> None:
        from claudeloop.cli.commands.watch import sys_stdout_isatty

        result = sys_stdout_isatty()
        assert isinstance(result, bool)
