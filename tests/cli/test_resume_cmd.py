"""Tests for cli/commands/resume.py — resume command error and success paths."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from claudeloop.cli.app import app

runner = CliRunner()
_ENV = {"NO_COLOR": "1", "TERM": "dumb"}


class TestResumeSuccess:
    def test_resume_with_session_id(self, tmp_path: Path) -> None:
        mock_context = MagicMock()
        mock_context.run_id = "test-run-1"
        mock_context.trace_id = "test-trace-1"
        mock_context.run_dir = MagicMock()

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.reason = "done"

        with (
            patch("claudeloop.cli.commands.resume.load_config") as mock_config,
            patch("claudeloop.cli.commands.resume.configure_logging"),
            patch("claudeloop.cli.commands.resume.bootstrap") as mock_bootstrap,
            patch(
                "claudeloop.cli.commands.resume.resume_explicit", new_callable=AsyncMock
            ) as mock_resume,
        ):
            mock_config.return_value = MagicMock(
                log_file=None,
                log_level="INFO",
                done_marker=None,
            )
            mock_bootstrap.build_runner.return_value = mock_context
            mock_resume.return_value = mock_result

            result = runner.invoke(
                app,
                ["resume", "--session-id", "sess-123"],
                env=_ENV,
            )
            assert result.exit_code == 0
            assert "Done:" in result.output

    def test_resume_failure(self, tmp_path: Path) -> None:
        mock_context = MagicMock()
        mock_context.run_id = "test-run-1"
        mock_context.trace_id = "test-trace-1"
        mock_context.run_dir = MagicMock()

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.reason = "credits exhausted"

        with (
            patch("claudeloop.cli.commands.resume.load_config") as mock_config,
            patch("claudeloop.cli.commands.resume.configure_logging"),
            patch("claudeloop.cli.commands.resume.bootstrap") as mock_bootstrap,
            patch(
                "claudeloop.cli.commands.resume.resume_explicit", new_callable=AsyncMock
            ) as mock_resume,
        ):
            mock_config.return_value = MagicMock(
                log_file=None,
                log_level="INFO",
                done_marker=None,
            )
            mock_bootstrap.build_runner.return_value = mock_context
            mock_resume.return_value = mock_result

            result = runner.invoke(
                app,
                ["resume", "--session-id", "sess-123"],
                env=_ENV,
            )
            assert result.exit_code == 1

    def test_resume_stopped(self, tmp_path: Path) -> None:
        mock_context = MagicMock()
        mock_context.run_id = "test-run-1"
        mock_context.trace_id = "test-trace-1"
        mock_context.run_dir = MagicMock()

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.reason = "stopped by operator"

        with (
            patch("claudeloop.cli.commands.resume.load_config") as mock_config,
            patch("claudeloop.cli.commands.resume.configure_logging"),
            patch("claudeloop.cli.commands.resume.bootstrap") as mock_bootstrap,
            patch(
                "claudeloop.cli.commands.resume.resume_explicit", new_callable=AsyncMock
            ) as mock_resume,
        ):
            mock_config.return_value = MagicMock(
                log_file=None,
                log_level="INFO",
                done_marker=None,
            )
            mock_bootstrap.build_runner.return_value = mock_context
            mock_resume.return_value = mock_result

            result = runner.invoke(
                app,
                ["resume", "--session-id", "sess-123"],
                env=_ENV,
            )
            assert result.exit_code == 130

    def test_resume_auto_resolve_no_sessions(self) -> None:
        from claudeloop.domain.errors import InvalidSessionSelectorError

        with (
            patch("claudeloop.cli.commands.resume.load_config") as mock_config,
            patch("claudeloop.cli.commands.resume.configure_logging"),
            patch("claudeloop.cli.commands.resume.bootstrap") as mock_bootstrap,
            patch("claudeloop.cli.commands.resume.resolve_most_recent") as mock_resolve,
        ):
            mock_config.return_value = MagicMock(
                log_file=None,
                log_level="INFO",
                done_marker=None,
            )
            mock_bootstrap.build_session_catalog.return_value = MagicMock()
            mock_resolve.side_effect = InvalidSessionSelectorError("no sessions")

            result = runner.invoke(
                app,
                ["resume"],
                env=_ENV,
            )
            assert result.exit_code == 1
            assert "no sessions" in result.output
