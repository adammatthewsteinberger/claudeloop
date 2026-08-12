"""Infrastructure tests for RunSnapshotBuilder."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from claudeloop.infrastructure.rundir import RunDirectory, runs_root_for
from claudeloop.infrastructure.snapshot import (
    RunSnapshotBuilder,
    locate_claude_transcript,
    sanitize_cwd_for_project_dir,
)
from tests.application.fakes import FakeClock


class RecordingBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    def publish(self, event_type: str, state: dict[str, object]) -> None:
        self.events.append((event_type, state))


def _builder(tmp_path: Path) -> tuple[RunSnapshotBuilder, RunDirectory, RecordingBus]:
    run_dir = RunDirectory.create(runs_root_for(tmp_path), cwd=tmp_path)
    bus = RecordingBus()
    clock = FakeClock(start=datetime(2026, 8, 12, 16, 0, tzinfo=timezone.utc))
    builder = RunSnapshotBuilder(run_dir, state_bus=bus, home=tmp_path / "home", clock=clock)
    return builder, run_dir, bus


def test_sanitize_cwd() -> None:
    assert sanitize_cwd_for_project_dir("/Users/a/git/x") == "-Users-a-git-x"


def test_builder_writes_latest_and_immutable(tmp_path: Path) -> None:
    builder, run_dir, bus = _builder(tmp_path)
    ref = builder.emit("started", context={"session_id": None})
    assert ref is not None
    assert (run_dir.snapshots_root / "latest.json").is_file()
    immutables = list(run_dir.snapshots_root.glob("*-started.json"))
    assert len(immutables) == 1
    assert bus.events[-1][0] == "snapshot.written"
    assert bus.events[-1][1]["snapshot_digest"] == ref.digest
    assert bus.events[-1][1]["snapshot_reason"] == "started"


def test_status_digest_skip(tmp_path: Path) -> None:
    builder, run_dir, bus = _builder(tmp_path)
    first = builder.emit("status", context={"attempt": 1, "phase": "SENDING"})
    assert first is not None
    n = len(bus.events)
    second = builder.emit("status", context={"attempt": 1, "phase": "SENDING"})
    assert second is None
    assert len(bus.events) == n
    third = builder.emit("status", context={"attempt": 2, "phase": "SENDING"})
    assert third is not None
    assert bus.events[-1][0] == "snapshot.latest"


def test_bundle_and_missing_transcript(tmp_path: Path) -> None:
    builder, run_dir, bus = _builder(tmp_path)
    ref = builder.emit(
        "manual",
        context={"session_id": "sid-1", "cwd": str(tmp_path)},
        bundle=True,
    )
    assert ref is not None
    assert ref.bundle_path is not None
    payload = json.loads((run_dir.root / ref.path).read_text(encoding="utf-8"))
    assert payload["claude_session"]["found"] is False
    assert "api_key" not in json.dumps(payload)


def test_transcript_present_copied(tmp_path: Path) -> None:
    home = tmp_path / "home"
    cwd = str(tmp_path / "proj")
    slug = sanitize_cwd_for_project_dir(cwd)
    project = home / ".claude" / "projects" / slug
    project.mkdir(parents=True)
    transcript = project / "abc123.jsonl"
    transcript.write_text('{"type":"user"}\n', encoding="utf-8")

    run_dir = RunDirectory.create(runs_root_for(tmp_path), cwd=tmp_path)
    bus = RecordingBus()
    builder = RunSnapshotBuilder(run_dir, state_bus=bus, home=home)
    ref = builder.emit(
        "finished",
        context={"session_id": "abc123", "cwd": cwd},
        bundle=True,
    )
    assert ref is not None
    payload = json.loads((run_dir.snapshots_root / "latest.json").read_text(encoding="utf-8"))
    assert payload["claude_session"]["found"] is True
    assert payload["claude_session"]["transcript_copied"].endswith("abc123.jsonl")
    assert (run_dir.snapshots_root / "claude" / "abc123.jsonl").is_file()


def test_locate_claude_transcript_helpers(tmp_path: Path) -> None:
    assert locate_claude_transcript(session_id=None, cwd="/x")["found"] is False
    assert locate_claude_transcript(session_id="s", cwd=None)["found"] is False
    missing = locate_claude_transcript(session_id="s", cwd="/nope", home=tmp_path)
    assert missing["found"] is False
