from __future__ import annotations

from pathlib import Path

from claudeloop.infrastructure.agent.options import (
    DEFAULT_MAX_BUFFER_SIZE,
    build_turn_options,
)
from claudeloop.infrastructure.state_bus import FileStateBus


def test_default_max_buffer_size_exceeds_sdk_1mb_floor() -> None:
    options = build_turn_options(cwd="/tmp")
    assert options.max_buffer_size == DEFAULT_MAX_BUFFER_SIZE
    assert DEFAULT_MAX_BUFFER_SIZE > 1024 * 1024


def test_max_buffer_size_override() -> None:
    options = build_turn_options(cwd="/tmp", max_buffer_size=2 * 1024 * 1024)
    assert options.max_buffer_size == 2 * 1024 * 1024


def test_effort_and_partial_messages_wired() -> None:
    options = build_turn_options(
        cwd="/tmp",
        model="claude-sonnet-4-5",
        effort="medium",
        include_partial_messages=True,
    )
    assert options.model == "claude-sonnet-4-5"
    assert options.effort == "medium"
    assert options.include_partial_messages is True


def test_file_state_bus_publish_and_status(tmp_path: Path) -> None:
    status = tmp_path / "status.json"
    bus = tmp_path / "bus.jsonl"
    publisher = FileStateBus(status_path=status, bus_path=bus, run_id="r1")
    publisher.publish("phase.running", {"phase": "RUNNING", "attempt": 1, "status": "active"})
    assert status.is_file()
    text = status.read_text(encoding="utf-8")
    assert "RUNNING" in text
    assert "r1" in bus.read_text(encoding="utf-8")
