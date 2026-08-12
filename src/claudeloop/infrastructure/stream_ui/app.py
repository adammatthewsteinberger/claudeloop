"""Textual StreamApp — multi-pane live / follow / replay UI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Footer, Header, RichLog, Static

from claudeloop.infrastructure.stream_ui import BufferingStreamUi, StreamUiState


class StreamApp(App[None]):
    CSS = """
    #header-bar { height: 3; dock: top; }
    #assistant { height: 1fr; border: solid $accent; }
    #tools { width: 40%; border: solid $primary; }
    #main { height: 1fr; }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("p", "toggle_pause", "Pause follow"),
        ("space", "toggle_play", "Play/Pause replay"),
        ("[", "prev_turn", "Prev turn"),
        ("]", "next_turn", "Next turn"),
    ]

    paused: reactive[bool] = reactive(False)

    def __init__(
        self,
        *,
        events_path: Path,
        follow: bool = True,
        replay: bool = False,
        speed: float = 1.0,
        initial: StreamUiState | None = None,
        live_source: BufferingStreamUi | None = None,
    ) -> None:
        super().__init__()
        self.events_path = events_path
        self.follow = follow
        self.replay = replay
        self.speed = speed
        self.state = initial or StreamUiState()
        self.live_source = live_source
        self._offset = 0
        self._records: list[dict[str, Any]] = []
        self._replay_index = 0
        self._turn_starts: list[int] = []
        self._playing = True

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(self._header_text(), id="header-bar")
        with Horizontal(id="main"):
            yield RichLog(id="assistant", highlight=True, markup=True)
            yield RichLog(id="tools", highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        if self.replay:
            self._load_all()
            self.set_interval(0.05, self._tick_replay)
        else:
            self.set_interval(0.2, self._tick_follow)
            if self.live_source is not None:
                self.set_interval(0.1, self._tick_live)

    def _header_text(self) -> str:
        s = self.state
        return (
            f"run={s.run_id}  trace={s.trace_id}  model={s.model}  "
            f"effort={s.effort}  attempt={s.attempt}  phase={s.phase}  "
            f"spend=${s.spend:.4f}"
        )

    def _refresh_header(self) -> None:
        self.query_one("#header-bar", Static).update(self._header_text())

    def _append_assistant(self, text: str) -> None:
        if text:
            self.query_one("#assistant", RichLog).write(text)

    def _append_tool(self, line: str) -> None:
        self.query_one("#tools", RichLog).write(line)

    def _load_all(self) -> None:
        if not self.events_path.is_file():
            return
        self._records = []
        self._turn_starts = []
        with self.events_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("event_type") == "chatter.prompt":
                    self._turn_starts.append(len(self._records))
                self._records.append(record)
        if not self._turn_starts and self._records:
            self._turn_starts = [0]

    def _apply_record(self, record: dict[str, Any]) -> None:
        et = record.get("event_type")
        payload = record.get("payload") or {}
        if record.get("trace_id"):
            self.state.trace_id = str(record["trace_id"])
        if record.get("run_id"):
            self.state.run_id = str(record["run_id"])
        if et == "chatter.delta":
            self._append_assistant(str(payload.get("text") or ""))
        elif et == "chatter.prompt":
            self.query_one("#assistant", RichLog).clear()
            preview = payload.get("text") or payload.get("preview") or ""
            self._append_assistant(f"[dim]prompt:[/dim] {preview}\n\n")
        elif et == "chatter.assistant":
            text = payload.get("text") or payload.get("preview") or ""
            self._append_assistant(str(text))
        elif et == "chatter.tool":
            name = payload.get("name") or "tool"
            preview = payload.get("preview") or payload.get("text") or ""
            self._append_tool(f"{name}: {preview}")
        elif et == "model.profile_changed":
            self.state.model = str(payload.get("model") or self.state.model)
            self.state.effort = str(payload.get("effort") or self.state.effort)
        elif et == "turn.starting":
            attempt = record.get("attempt")
            if isinstance(attempt, int):
                self.state.attempt = attempt
        self._refresh_header()

    def _tick_follow(self) -> None:
        if self.paused or not self.follow:
            return
        if not self.events_path.is_file():
            return
        with self.events_path.open("r", encoding="utf-8") as fh:
            fh.seek(self._offset)
            chunk = fh.read()
            self._offset = fh.tell()
        for line in chunk.splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            self._apply_record(record)

    def _tick_live(self) -> None:
        if self.live_source is None or self.paused:
            return
        while self.live_source.deltas:
            text, _turn_id, _seq = self.live_source.deltas.pop(0)
            self._append_assistant(text)
        self.state = self.live_source.state
        self._refresh_header()

    def _tick_replay(self) -> None:
        if not self._playing or self.paused:
            return
        if self._replay_index >= len(self._records):
            return
        # Speed 0 = as fast as possible (apply several records per tick).
        n = 1 if self.speed > 0 else 20
        for _ in range(n):
            if self._replay_index >= len(self._records):
                break
            self._apply_record(self._records[self._replay_index])
            self._replay_index += 1

    def action_toggle_pause(self) -> None:
        self.paused = not self.paused

    def action_toggle_play(self) -> None:
        if self.replay:
            self._playing = not self._playing
        else:
            self.paused = not self.paused

    def action_prev_turn(self) -> None:
        if not self.replay or not self._turn_starts:
            return
        # Find previous turn start before current index.
        current = self._replay_index
        prev = 0
        for start in self._turn_starts:
            if start < current:
                prev = start
            else:
                break
        self.query_one("#assistant", RichLog).clear()
        self.query_one("#tools", RichLog).clear()
        self._replay_index = prev
        self._apply_record(self._records[prev])
        self._replay_index = prev + 1

    def action_next_turn(self) -> None:
        if not self.replay or not self._turn_starts:
            return
        current = self._replay_index
        nxt = None
        for start in self._turn_starts:
            if start >= current:
                nxt = start
                break
        if nxt is None:
            return
        self.query_one("#assistant", RichLog).clear()
        self.query_one("#tools", RichLog).clear()
        self._replay_index = nxt
        self._apply_record(self._records[nxt])
        self._replay_index = nxt + 1
