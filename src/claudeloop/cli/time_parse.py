"""Parse --wind-down-at time specifications.

Supports:
- ISO8601 absolute timestamps: 2026-08-17T15:30:00
- Relative durations: +2h, +90m, +30s, +1h30m
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta


def parse_wind_down_at(spec: str, *, now: datetime) -> datetime:
    """Parse a --wind-down-at value into an absolute deadline.

    Args:
        spec: Either an ISO8601 timestamp or a +duration (e.g. +2h, +90m).
        now: Current time for resolving relative durations.

    Returns:
        Absolute datetime deadline.

    Raises:
        ValueError: If the spec is invalid.
    """
    spec = spec.strip()
    if not spec:
        raise ValueError("--wind-down-at must not be blank")

    # Relative duration: +2h, +90m, +30s, +1h30m
    if spec.startswith("+"):
        duration_str = spec[1:].strip()
        if not duration_str:
            raise ValueError("duration after '+' must not be blank")
        delta = _parse_duration(duration_str)
        return now + delta

    # Absolute ISO8601 timestamp
    try:
        return datetime.fromisoformat(spec)
    except ValueError as exc:
        raise ValueError(
            f"--wind-down-at must be ISO8601 timestamp or +duration, got {spec!r}"
        ) from exc


def _parse_duration(spec: str) -> timedelta:
    """Parse a duration string like 2h, 90m, 30s, 1h30m into a timedelta.

    Args:
        spec: Duration string (e.g. "2h", "90m", "1h30m").

    Returns:
        timedelta representing the duration.

    Raises:
        ValueError: If the spec is invalid.
    """
    # Pattern: optional digits followed by h/m/s, repeatable
    # Anchored to ensure the entire string matches the expected format
    pattern = r"^(\d+[hms])+$"
    if not re.match(pattern, spec.lower()):
        raise ValueError(f"invalid duration format {spec!r}, expected e.g. 2h, 90m, 1h30m")

    # Extract all (value, unit) pairs
    matches = re.findall(r"(\d+)([hms])", spec.lower())

    total = timedelta()
    for value_str, unit in matches:
        value = int(value_str)
        if unit == "h":
            total += timedelta(hours=value)
        elif unit == "m":
            total += timedelta(minutes=value)
        elif unit == "s":
            total += timedelta(seconds=value)

    if total <= timedelta(0):
        raise ValueError(f"duration must be positive, got {spec!r}")

    return total
