"""Events sink trace/turn binding and chatter helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from claudeloop.infrastructure.chatter_log import chatter_payload
from claudeloop.infrastructure.events import JsonlRunEventSink
from claudeloop.infrastructure.stream_ui import dump_transcript, iter_event_records


def test_event_sink_includes_trace_and_turn(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    sink = JsonlRunEventSink(path, run_id="r1", trace_id="t1")
    sink.bind(turn_id="turn-a", attempt=2, phase="RUNNING")
    sink.emit("chatter.prompt", {"text": "hello"})
    records = list(iter_event_records(path))
    assert len(records) == 1
    assert records[0]["trace_id"] == "t1"
    assert records[0]["turn_id"] == "turn-a"
    assert records[0]["event_type"] == "chatter.prompt"


def test_chatter_payload_modes() -> None:
    assert chatter_payload("x", mode="off") is None
    summary = chatter_payload("hello world", mode="summary")
    assert summary is not None
    assert "preview" in summary
    full = chatter_payload("hello world", mode="full")
    assert full is not None
    assert full["text"] == "hello world"


def test_dump_transcript(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text(
        '{"event_type":"chatter.delta","payload":{"text":"Hi"}}\n'
        '{"event_type":"chatter.assistant","payload":{"text":" there"}}\n',
        encoding="utf-8",
    )
    dump_transcript(path)
    out = capsys.readouterr().out
    assert "Hi" in out
    assert "there" in out
