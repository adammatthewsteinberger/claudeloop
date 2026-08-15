"""Tests for infrastructure/api/binder.py — Click command tree builder."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import click
from click.testing import CliRunner

from claudeloop.infrastructure.api.binder import (
    _ensure_group,
    _make_click_command,
    build_api_click_group,
)


class TestEnsureGroup:
    def test_creates_new_group(self) -> None:
        parent = click.Group("root")
        child = _ensure_group(parent, "child")
        assert isinstance(child, click.Group)
        assert parent.commands["child"] is child

    def test_reuses_existing_group(self) -> None:
        parent = click.Group("root")
        first = _ensure_group(parent, "child")
        second = _ensure_group(parent, "child")
        assert first is second

    def test_replaces_non_group_command(self) -> None:
        parent = click.Group("root")
        parent.add_command(click.Command("child", callback=lambda: None), "child")
        group = _ensure_group(parent, "child")
        assert isinstance(group, click.Group)


class TestMakeClickCommand:
    def test_creates_command_with_params(self) -> None:
        method = MagicMock()
        method.path = "messages.create"
        method.method_name = "create"
        method.chain = ["messages"]

        gateway = MagicMock()

        with patch(
            "claudeloop.infrastructure.api.binder.resolve_callable"
        ) as mock_resolve:
            import inspect

            def dummy_fn(*, model: str = "claude-sonnet") -> None:
                pass

            mock_resolve.return_value = dummy_fn
            cmd = _make_click_command(method, gateway)

        assert isinstance(cmd, click.Command)
        assert cmd.name == "create"
        param_names = [p.name for p in cmd.params]
        assert "json" in param_names
        assert "json_file" in param_names
        assert "raw" in param_names
        assert "stream" in param_names
        assert "max_items" in param_names


class TestBuildApiClickGroup:
    def test_builds_group_with_commands(self) -> None:
        gateway = MagicMock()
        group = build_api_click_group(gateway=gateway)
        assert isinstance(group, click.Group)

    def test_help_output(self) -> None:
        gateway = MagicMock()
        group = build_api_click_group(gateway=gateway)
        runner = CliRunner()
        result = runner.invoke(group, ["--help"])
        assert result.exit_code == 0
        assert "api" in result.output.lower() or "SDK" in result.output

    def test_unknown_provider_raises(self) -> None:
        gateway = MagicMock()
        group = build_api_click_group(gateway=gateway)
        runner = CliRunner()
        result = runner.invoke(group, ["--provider", "nonexistent", "messages"])
        assert result.exit_code != 0
        assert "unknown provider" in result.output
