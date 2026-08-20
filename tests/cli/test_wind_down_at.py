"""Tests for cli/time_parse.py --wind-down-at parser.

Covers both absolute ISO-8601 timestamps and relative durations (+2h, +90m).
"""

from __future__ import annotations

from datetime import datetime

import pytest

from claudeloop.cli.time_parse import parse_wind_down_at


class TestParseWindDownAt:
    """Tests for parse_wind_down_at."""

    def test_absolute_iso8601_basic(self) -> None:
        """Parse a basic ISO-8601 timestamp."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        spec = "2026-08-17T15:30:00"
        result = parse_wind_down_at(spec, now=now)
        assert result == datetime(2026, 8, 17, 15, 30, 0)

    def test_absolute_iso8601_with_tz(self) -> None:
        """Parse an ISO-8601 timestamp with timezone."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        spec = "2026-08-17T15:30:00+00:00"
        result = parse_wind_down_at(spec, now=now)
        # fromisoformat handles timezone-aware datetimes
        assert result.year == 2026
        assert result.month == 8
        assert result.day == 17

    def test_absolute_iso8601_date_only(self) -> None:
        """Parse an ISO-8601 date-only string."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        spec = "2026-08-20"
        result = parse_wind_down_at(spec, now=now)
        assert result == datetime(2026, 8, 20, 0, 0, 0)

    def test_relative_hours_only(self) -> None:
        """Parse +2h relative duration."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        spec = "+2h"
        result = parse_wind_down_at(spec, now=now)
        assert result == datetime(2026, 8, 17, 14, 0, 0)

    def test_relative_minutes_only(self) -> None:
        """Parse +90m relative duration."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        spec = "+90m"
        result = parse_wind_down_at(spec, now=now)
        assert result == datetime(2026, 8, 17, 13, 30, 0)

    def test_relative_seconds_only(self) -> None:
        """Parse +30s relative duration."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        spec = "+30s"
        result = parse_wind_down_at(spec, now=now)
        assert result == datetime(2026, 8, 17, 12, 0, 30)

    def test_relative_compound_duration(self) -> None:
        """Parse +1h30m compound duration."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        spec = "+1h30m"
        result = parse_wind_down_at(spec, now=now)
        assert result == datetime(2026, 8, 17, 13, 30, 0)

    def test_relative_all_units(self) -> None:
        """Parse +2h15m30s compound duration."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        spec = "+2h15m30s"
        result = parse_wind_down_at(spec, now=now)
        assert result == datetime(2026, 8, 17, 14, 15, 30)

    def test_relative_uppercase_units(self) -> None:
        """Parse +2H15M with uppercase units."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        spec = "+2H15M"
        result = parse_wind_down_at(spec, now=now)
        assert result == datetime(2026, 8, 17, 14, 15, 0)

    def test_relative_mixed_case(self) -> None:
        """Parse +2H15m with mixed-case units."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        spec = "+2H15m"
        result = parse_wind_down_at(spec, now=now)
        assert result == datetime(2026, 8, 17, 14, 15, 0)

    def test_whitespace_stripped(self) -> None:
        """Parse with leading/trailing whitespace."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        spec = "  +2h  "
        result = parse_wind_down_at(spec, now=now)
        assert result == datetime(2026, 8, 17, 14, 0, 0)

    def test_blank_spec_raises(self) -> None:
        """Empty string raises ValueError."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        with pytest.raises(ValueError, match="must not be blank"):
            parse_wind_down_at("", now=now)

    def test_whitespace_only_spec_raises(self) -> None:
        """Whitespace-only string raises ValueError."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        with pytest.raises(ValueError, match="must not be blank"):
            parse_wind_down_at("   ", now=now)

    def test_plus_without_duration_raises(self) -> None:
        """'+' with no duration raises ValueError."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        with pytest.raises(ValueError, match="duration after.*must not be blank"):
            parse_wind_down_at("+", now=now)

    def test_plus_with_whitespace_only_raises(self) -> None:
        """'+' with only whitespace raises ValueError."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        with pytest.raises(ValueError, match="duration after.*must not be blank"):
            parse_wind_down_at("+   ", now=now)

    def test_invalid_duration_format_no_unit(self) -> None:
        """Number without unit raises ValueError."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        with pytest.raises(ValueError, match="invalid duration format"):
            parse_wind_down_at("+90", now=now)

    def test_invalid_duration_format_wrong_unit(self) -> None:
        """Invalid unit (d for days) raises ValueError."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        with pytest.raises(ValueError, match="invalid duration format"):
            parse_wind_down_at("+1d", now=now)

    def test_invalid_duration_format_no_number(self) -> None:
        """Unit without number raises ValueError."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        with pytest.raises(ValueError, match="invalid duration format"):
            parse_wind_down_at("+h", now=now)

    def test_invalid_duration_format_mixed_invalid(self) -> None:
        """Mixed valid and invalid units raises ValueError."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        with pytest.raises(ValueError, match="invalid duration format"):
            parse_wind_down_at("+1h30x", now=now)

    def test_zero_duration_raises(self) -> None:
        """Zero duration raises ValueError."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        with pytest.raises(ValueError, match="duration must be positive"):
            parse_wind_down_at("+0h", now=now)

    def test_zero_compound_duration_raises(self) -> None:
        """Compound duration that sums to zero raises ValueError."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        with pytest.raises(ValueError, match="duration must be positive"):
            parse_wind_down_at("+0h0m0s", now=now)

    def test_invalid_iso8601_raises(self) -> None:
        """Invalid ISO-8601 format raises ValueError."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        with pytest.raises(ValueError, match="must be ISO8601 timestamp or \\+duration"):
            parse_wind_down_at("not-a-date", now=now)

    def test_invalid_iso8601_partial_raises(self) -> None:
        """Partially valid ISO-8601 raises ValueError."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        with pytest.raises(ValueError, match="must be ISO8601 timestamp or \\+duration"):
            parse_wind_down_at("2026-13-01", now=now)  # Invalid month

    def test_relative_large_values(self) -> None:
        """Parse large relative values."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        spec = "+48h"
        result = parse_wind_down_at(spec, now=now)
        assert result == datetime(2026, 8, 19, 12, 0, 0)

    def test_relative_multiple_of_same_unit(self) -> None:
        """Parse multiple occurrences of same unit (sums them)."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        spec = "+1h2h"
        result = parse_wind_down_at(spec, now=now)
        assert result == datetime(2026, 8, 17, 15, 0, 0)

    def test_relative_seconds_followed_by_other_units(self) -> None:
        """Parse duration with seconds not at the end."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        spec = "+30s1h15m"
        result = parse_wind_down_at(spec, now=now)
        assert result == datetime(2026, 8, 17, 13, 15, 30)

    def test_relative_multiple_seconds(self) -> None:
        """Parse duration with multiple second components."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        spec = "+10s20s30s"
        result = parse_wind_down_at(spec, now=now)
        assert result == datetime(2026, 8, 17, 12, 1, 0)

    def test_relative_seconds_middle_of_sequence(self) -> None:
        """Parse duration with seconds in the middle followed by hours."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        spec = "+1m30s2h"
        result = parse_wind_down_at(spec, now=now)
        assert result == datetime(2026, 8, 17, 14, 1, 30)

    def test_relative_hours_seconds_minutes(self) -> None:
        """Parse duration with seconds between hours and minutes."""
        now = datetime(2026, 8, 17, 12, 0, 0)
        spec = "+1h30s1m"
        result = parse_wind_down_at(spec, now=now)
        assert result == datetime(2026, 8, 17, 13, 1, 30)
