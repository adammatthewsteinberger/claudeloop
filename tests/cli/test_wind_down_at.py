"""Tests for --wind-down-at parsing and deadline-driven wind-down."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from claudeloop.cli.time_parse import parse_wind_down_at


class TestParseWindDownAt:
    """Test time parsing for --wind-down-at."""

    def test_iso8601_absolute(self) -> None:
        """Parse absolute ISO8601 timestamp."""
        now = datetime(2026, 8, 17, 10, 0, 0)
        result = parse_wind_down_at("2026-08-17T15:30:00", now=now)
        assert result == datetime(2026, 8, 17, 15, 30, 0)

    def test_relative_hours(self) -> None:
        """Parse relative duration in hours."""
        now = datetime(2026, 8, 17, 10, 0, 0)
        result = parse_wind_down_at("+2h", now=now)
        assert result == datetime(2026, 8, 17, 12, 0, 0)

    def test_relative_minutes(self) -> None:
        """Parse relative duration in minutes."""
        now = datetime(2026, 8, 17, 10, 0, 0)
        result = parse_wind_down_at("+90m", now=now)
        assert result == datetime(2026, 8, 17, 11, 30, 0)

    def test_relative_seconds(self) -> None:
        """Parse relative duration in seconds."""
        now = datetime(2026, 8, 17, 10, 0, 0)
        result = parse_wind_down_at("+30s", now=now)
        assert result == datetime(2026, 8, 17, 10, 0, 30)

    def test_relative_mixed(self) -> None:
        """Parse relative duration with mixed units."""
        now = datetime(2026, 8, 17, 10, 0, 0)
        result = parse_wind_down_at("+1h30m", now=now)
        assert result == datetime(2026, 8, 17, 11, 30, 0)

    def test_relative_complex(self) -> None:
        """Parse complex relative duration."""
        now = datetime(2026, 8, 17, 10, 0, 0)
        result = parse_wind_down_at("+2h15m30s", now=now)
        assert result == datetime(2026, 8, 17, 12, 15, 30)

    def test_blank_rejected(self) -> None:
        """Blank spec raises ValueError."""
        now = datetime(2026, 8, 17, 10, 0, 0)
        with pytest.raises(ValueError, match="must not be blank"):
            parse_wind_down_at("", now=now)

    def test_whitespace_rejected(self) -> None:
        """Whitespace-only spec raises ValueError."""
        now = datetime(2026, 8, 17, 10, 0, 0)
        with pytest.raises(ValueError, match="must not be blank"):
            parse_wind_down_at("   ", now=now)

    def test_invalid_duration_format(self) -> None:
        """Invalid duration format raises ValueError."""
        now = datetime(2026, 8, 17, 10, 0, 0)
        with pytest.raises(ValueError, match="invalid duration format"):
            parse_wind_down_at("+xyz", now=now)

    def test_duration_without_plus(self) -> None:
        """Duration without + prefix is treated as ISO8601 and fails."""
        now = datetime(2026, 8, 17, 10, 0, 0)
        with pytest.raises(ValueError, match="ISO8601 timestamp or \\+duration"):
            parse_wind_down_at("2h", now=now)

    def test_zero_duration_rejected(self) -> None:
        """Zero duration raises ValueError."""
        now = datetime(2026, 8, 17, 10, 0, 0)
        with pytest.raises(ValueError, match="duration must be positive"):
            parse_wind_down_at("+0h", now=now)

    def test_negative_duration_rejected(self) -> None:
        """Negative duration is treated as invalid format."""
        now = datetime(2026, 8, 17, 10, 0, 0)
        # The regex won't match negative numbers, so it becomes "invalid format"
        with pytest.raises(ValueError, match="invalid duration format"):
            parse_wind_down_at("+-2h", now=now)

    def test_invalid_iso8601(self) -> None:
        """Invalid ISO8601 raises ValueError."""
        now = datetime(2026, 8, 17, 10, 0, 0)
        with pytest.raises(ValueError, match="ISO8601 timestamp or \\+duration"):
            parse_wind_down_at("not-a-date", now=now)

    def test_plus_without_duration(self) -> None:
        """+duration with no duration raises ValueError."""
        now = datetime(2026, 8, 17, 10, 0, 0)
        with pytest.raises(ValueError, match="duration after '\\+' must not be blank"):
            parse_wind_down_at("+", now=now)

    def test_plus_with_whitespace(self) -> None:
        """+duration with only whitespace raises ValueError."""
        now = datetime(2026, 8, 17, 10, 0, 0)
        with pytest.raises(ValueError, match="duration after '\\+' must not be blank"):
            parse_wind_down_at("+   ", now=now)
