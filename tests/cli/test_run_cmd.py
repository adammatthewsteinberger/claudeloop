"""Tests for cli/commands/run.py — _parse_connector and run command logic."""

from __future__ import annotations

import json

import pytest

from claudeloop.cli.commands.run import _parse_connector


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
