"""Tests for cli/commands/run.py — _parse_connector and run command logic."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from claudeloop.cli.app import app
from claudeloop.cli.commands.run import _parse_connector

runner = CliRunner()
_ENV = {"NO_COLOR": "1", "TERM": "dumb"}


class TestParseConnector:
    def test_name_url(self) -> None:
        name, cfg = _parse_connector("myconn=https://example.com")
        assert name == "myconn"
        assert cfg == {"url": "https://example.com"}

    def test_name_json(self) -> None:
        spec = 'myconn={"url": "http://localhost:8080", "key": "val"}'
        name, cfg = _parse_connector(spec)
        assert name == "myconn"
        assert cfg["url"] == "http://localhost:8080"
        assert cfg["key"] == "val"

    def test_no_equals_raises(self) -> None:
        with pytest.raises(ValueError, match="connector must be NAME="):
            _parse_connector("noequals")

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="connector name must not be blank"):
            _parse_connector("=value")

    def test_whitespace_trimmed(self) -> None:
        name, cfg = _parse_connector("  conn  =  http://x  ")
        assert name == "conn"
        assert cfg == {"url": "http://x"}

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(json.JSONDecodeError):
            _parse_connector("conn={bad json}")


class TestRunCommandErrors:
    def test_run_bad_plan_file(self) -> None:
        result = runner.invoke(app, ["run", "/does/not/exist.md"], env=_ENV)
        assert result.exit_code != 0

    def test_run_invalid_slash(self, tmp_path: Path) -> None:
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\nDo something", encoding="utf-8")
        result = runner.invoke(
            app,
            ["run", str(plan), "--slash", "no-prefix"],
            env=_ENV,
        )
        assert result.exit_code == 2
        assert "must start with" in result.output

    def test_run_invalid_connector(self, tmp_path: Path) -> None:
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\nDo something", encoding="utf-8")
        result = runner.invoke(
            app,
            ["run", str(plan), "--connector", "noequalssign"],
            env=_ENV,
        )
        assert result.exit_code == 2
        assert "Invalid --connector" in result.output


class TestRunSuccess:
    def test_run_success_path(self, tmp_path: Path) -> None:
        plan = tmp_path / "plan.md"
        plan.write_text("# Test Plan\nDo something\n", encoding="utf-8")

        mock_context = MagicMock()
        mock_context.run_id = "test-run-1"
        mock_context.trace_id = "test-trace-1"
        mock_context.run_dir = MagicMock()
        mock_context.run_dir.events_path = tmp_path / "events.jsonl"

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.reason = "done"

        with (
            patch("claudeloop.cli.commands.run.load_config") as mock_config,
            patch("claudeloop.cli.commands.run.configure_logging"),
            patch("claudeloop.cli.commands.run.parse_plan_file") as mock_parse,
            patch("claudeloop.cli.commands.run.bootstrap") as mock_bootstrap,
            patch("claudeloop.cli.commands.run.run_from_plan_file", new_callable=AsyncMock) as mock_run,
        ):
            mock_config.return_value = MagicMock(
                log_file=None, log_level="INFO", done_marker=None,
            )
            mock_parse.return_value = MagicMock()
            mock_bootstrap.build_runner.return_value = mock_context
            mock_run.return_value = mock_result

            result = runner.invoke(
                app,
                ["run", str(plan)],
                env=_ENV,
            )
            assert result.exit_code == 0
            assert "Done:" in result.output

    def test_run_failure_path(self, tmp_path: Path) -> None:
        plan = tmp_path / "plan.md"
        plan.write_text("# Test Plan\nDo something\n", encoding="utf-8")

        mock_context = MagicMock()
        mock_context.run_id = "test-run-1"
        mock_context.trace_id = "test-trace-1"
        mock_context.run_dir = MagicMock()

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.reason = "credits exhausted"

        with (
            patch("claudeloop.cli.commands.run.load_config") as mock_config,
            patch("claudeloop.cli.commands.run.configure_logging"),
            patch("claudeloop.cli.commands.run.parse_plan_file") as mock_parse,
            patch("claudeloop.cli.commands.run.bootstrap") as mock_bootstrap,
            patch("claudeloop.cli.commands.run.run_from_plan_file", new_callable=AsyncMock) as mock_run,
        ):
            mock_config.return_value = MagicMock(
                log_file=None, log_level="INFO", done_marker=None,
            )
            mock_parse.return_value = MagicMock()
            mock_bootstrap.build_runner.return_value = mock_context
            mock_run.return_value = mock_result

            result = runner.invoke(
                app,
                ["run", str(plan)],
                env=_ENV,
            )
            assert result.exit_code == 1

    def test_run_wind_down_path(self, tmp_path: Path) -> None:
        plan = tmp_path / "plan.md"
        plan.write_text("# Test Plan\nDo something\n", encoding="utf-8")

        mock_context = MagicMock()
        mock_context.run_id = "test-run-1"
        mock_context.trace_id = "test-trace-1"
        mock_context.run_dir = MagicMock()
        mock_context.run_dir.root = tmp_path
        (tmp_path / "HANDOFF.md").write_text("handoff info", encoding="utf-8")

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.reason = "wind-down: operator requested"

        with (
            patch("claudeloop.cli.commands.run.load_config") as mock_config,
            patch("claudeloop.cli.commands.run.configure_logging"),
            patch("claudeloop.cli.commands.run.parse_plan_file") as mock_parse,
            patch("claudeloop.cli.commands.run.bootstrap") as mock_bootstrap,
            patch("claudeloop.cli.commands.run.run_from_plan_file", new_callable=AsyncMock) as mock_run,
            patch("claudeloop.cli.commands.run.HANDOFF_MARKER_FILENAME", "HANDOFF.md"),
        ):
            mock_config.return_value = MagicMock(
                log_file=None, log_level="INFO", done_marker=None,
            )
            mock_parse.return_value = MagicMock()
            mock_bootstrap.build_runner.return_value = mock_context
            mock_run.return_value = mock_result

            result = runner.invoke(
                app,
                ["run", str(plan)],
                env=_ENV,
            )
            assert result.exit_code != 0

    def test_run_stopped_path(self, tmp_path: Path) -> None:
        plan = tmp_path / "plan.md"
        plan.write_text("# Test Plan\nDo something\n", encoding="utf-8")

        mock_context = MagicMock()
        mock_context.run_id = "test-run-1"
        mock_context.trace_id = "test-trace-1"
        mock_context.run_dir = MagicMock()
        mock_context.run_dir.stop_summary_path = tmp_path / "stop.json"

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.reason = "stopped by operator"

        with (
            patch("claudeloop.cli.commands.run.load_config") as mock_config,
            patch("claudeloop.cli.commands.run.configure_logging"),
            patch("claudeloop.cli.commands.run.parse_plan_file") as mock_parse,
            patch("claudeloop.cli.commands.run.bootstrap") as mock_bootstrap,
            patch("claudeloop.cli.commands.run.run_from_plan_file", new_callable=AsyncMock) as mock_run,
        ):
            mock_config.return_value = MagicMock(
                log_file=None, log_level="INFO", done_marker=None,
            )
            mock_parse.return_value = MagicMock()
            mock_bootstrap.build_runner.return_value = mock_context
            mock_run.return_value = mock_result

            result = runner.invoke(
                app,
                ["run", str(plan)],
                env=_ENV,
            )
            assert result.exit_code == 130

    def test_run_build_runner_value_error(self, tmp_path: Path) -> None:
        plan = tmp_path / "plan.md"
        plan.write_text("# Test Plan\nDo something\n", encoding="utf-8")

        with (
            patch("claudeloop.cli.commands.run.load_config") as mock_config,
            patch("claudeloop.cli.commands.run.configure_logging"),
            patch("claudeloop.cli.commands.run.parse_plan_file") as mock_parse,
            patch("claudeloop.cli.commands.run.bootstrap") as mock_bootstrap,
        ):
            mock_config.return_value = MagicMock(
                log_file=None, log_level="INFO", done_marker=None,
            )
            mock_parse.return_value = MagicMock()
            mock_bootstrap.build_runner.side_effect = ValueError("bad config")

            result = runner.invoke(
                app,
                ["run", str(plan)],
                env=_ENV,
            )
            assert result.exit_code == 2

    def test_run_build_runner_file_exists(self, tmp_path: Path) -> None:
        plan = tmp_path / "plan.md"
        plan.write_text("# Test Plan\nDo something\n", encoding="utf-8")

        with (
            patch("claudeloop.cli.commands.run.load_config") as mock_config,
            patch("claudeloop.cli.commands.run.configure_logging"),
            patch("claudeloop.cli.commands.run.parse_plan_file") as mock_parse,
            patch("claudeloop.cli.commands.run.bootstrap") as mock_bootstrap,
        ):
            mock_config.return_value = MagicMock(
                log_file=None, log_level="INFO", done_marker=None,
            )
            mock_parse.return_value = MagicMock()
            mock_bootstrap.build_runner.side_effect = FileExistsError("exists")

            result = runner.invoke(
                app,
                ["run", str(plan), "--run-id", "dupe"],
                env=_ENV,
            )
            assert result.exit_code == 2
            assert "already exists" in result.output

    def test_run_invalid_plan_error(self, tmp_path: Path) -> None:
        plan = tmp_path / "plan.md"
        plan.write_text("# Test Plan\nDo something\n", encoding="utf-8")

        with (
            patch("claudeloop.cli.commands.run.load_config") as mock_config,
            patch("claudeloop.cli.commands.run.configure_logging"),
            patch("claudeloop.cli.commands.run.parse_plan_file") as mock_parse,
        ):
            mock_config.return_value = MagicMock(
                log_file=None, log_level="INFO", done_marker=None,
            )
            from claudeloop.domain.errors import InvalidPlanError
            mock_parse.side_effect = InvalidPlanError("no heading")

            result = runner.invoke(
                app,
                ["run", str(plan)],
                env=_ENV,
            )
            assert result.exit_code == 1
            assert "Invalid plan" in result.output
