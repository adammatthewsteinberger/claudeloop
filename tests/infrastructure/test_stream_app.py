"""Tests for infrastructure/stream_ui/app.py — StreamApp Textual TUI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from claudeloop.infrastructure.stream_ui import BufferingStreamUi, StreamUiState
from claudeloop.infrastructure.stream_ui.app import StreamApp


def _write_events(path: Path, events: list[dict]) -> Path:
    f = path / "events.jsonl"
    f.write_text(
        "\n".join(json.dumps(e) for e in events) + "\n",
        encoding="utf-8",
    )
    return f


def _make_app(
    events_path: Path, *, replay: bool = False, follow: bool = True, **kwargs
) -> StreamApp:
    return StreamApp(
        events_path=events_path,
        replay=replay,
        follow=follow,
        **kwargs,
    )


class TestStreamAppInit:
    def test_defaults(self, tmp_path: Path) -> None:
        app = _make_app(tmp_path / "events.jsonl")
        assert app.follow is True
        assert app.replay is False
        assert app.speed == 1.0
        assert isinstance(app.state, StreamUiState)
        assert app._offset == 0
        assert app._records == []
        assert app._saw_delta is False

    def test_with_initial_state(self, tmp_path: Path) -> None:
        state = StreamUiState(run_id="r1", model="opus")
        app = _make_app(tmp_path / "events.jsonl", initial=state)
        assert app.state.run_id == "r1"
        assert app.state.model == "opus"

    def test_with_live_source(self, tmp_path: Path) -> None:
        live = BufferingStreamUi()
        app = _make_app(tmp_path / "events.jsonl", live_source=live)
        assert app.live_source is live


class TestStreamAppHeaderText:
    def test_header_text(self, tmp_path: Path) -> None:
        state = StreamUiState(
            run_id="r1",
            trace_id="t1",
            model="opus",
            effort="high",
            attempt=3,
            phase="RUNNING",
        )
        state.spend = 1.5
        app = _make_app(tmp_path / "events.jsonl", initial=state)
        text = app._header_text()
        assert "r1" in text
        assert "t1" in text
        assert "opus" in text
        assert "high" in text
        assert "3" in text
        assert "RUNNING" in text
        assert "1.5" in text


class TestStreamAppLoadAll:
    def test_load_all_with_prompts(self, tmp_path: Path) -> None:
        events = [
            {"event_type": "chatter.prompt", "payload": {"text": "first"}},
            {"event_type": "chatter.delta", "payload": {"text": "hi"}},
            {"event_type": "chatter.prompt", "payload": {"text": "second"}},
            {"event_type": "chatter.delta", "payload": {"text": "bye"}},
        ]
        f = _write_events(tmp_path, events)
        app = _make_app(f, replay=True)
        app._load_all()
        assert len(app._records) == 4
        assert app._turn_starts == [0, 2]

    def test_load_all_no_prompts(self, tmp_path: Path) -> None:
        events = [
            {"event_type": "chatter.delta", "payload": {"text": "hi"}},
        ]
        f = _write_events(tmp_path, events)
        app = _make_app(f, replay=True)
        app._load_all()
        assert len(app._records) == 1
        assert app._turn_starts == [0]

    def test_load_all_missing_file(self, tmp_path: Path) -> None:
        app = _make_app(tmp_path / "nope.jsonl", replay=True)
        app._load_all()
        assert app._records == []

    def test_load_all_skips_bad_json(self, tmp_path: Path) -> None:
        f = tmp_path / "events.jsonl"
        f.write_text(
            '{"event_type":"chatter.delta","payload":{"text":"ok"}}\n'
            "{bad}\n"
            "\n"
            '{"event_type":"chatter.delta","payload":{"text":"fine"}}\n',
            encoding="utf-8",
        )
        app = _make_app(f, replay=True)
        app._load_all()
        assert len(app._records) == 2


class TestStreamAppCompose:
    @pytest.mark.asyncio
    async def test_compose_widgets(self, tmp_path: Path) -> None:
        f = _write_events(tmp_path, [])
        app = _make_app(f, follow=False)
        async with app.run_test(size=(120, 40)):
            assert app.query_one("#assistant") is not None
            assert app.query_one("#tools") is not None
            assert app.query_one("#header-bar") is not None
            assert app.query_one("#thinking-bar") is not None


class TestStreamAppApplyRecord:
    @pytest.mark.asyncio
    async def test_apply_record_sets_trace_and_run(self, tmp_path: Path) -> None:
        events = [
            {
                "event_type": "chatter.delta",
                "payload": {"text": "hi"},
                "trace_id": "t1",
                "run_id": "r1",
            },
        ]
        f = _write_events(tmp_path, events)
        app = _make_app(f, follow=False)
        async with app.run_test(size=(120, 40)):
            app._apply_record(events[0])
            assert app.state.trace_id == "t1"
            assert app.state.run_id == "r1"

    @pytest.mark.asyncio
    async def test_apply_record_model_profile_changed(self, tmp_path: Path) -> None:
        events = [
            {"event_type": "model.profile_changed", "payload": {"model": "opus", "effort": "max"}},
        ]
        f = _write_events(tmp_path, events)
        app = _make_app(f, follow=False)
        async with app.run_test(size=(120, 40)):
            app._apply_record(events[0])
            assert app.state.model == "opus"
            assert app.state.effort == "max"

    @pytest.mark.asyncio
    async def test_apply_record_turn_starting(self, tmp_path: Path) -> None:
        events = [
            {"event_type": "turn.starting", "attempt": 5},
        ]
        f = _write_events(tmp_path, events)
        app = _make_app(f, follow=False)
        async with app.run_test(size=(120, 40)):
            app._apply_record(events[0])
            assert app.state.attempt == 5


class TestStreamAppTickFollow:
    @pytest.mark.asyncio
    async def test_tick_follow_reads_events(self, tmp_path: Path) -> None:
        events = [
            {"event_type": "chatter.delta", "payload": {"text": "hello"}},
        ]
        f = _write_events(tmp_path, events)
        app = _make_app(f, follow=True)
        async with app.run_test(size=(120, 40)):
            app._tick_follow()
            assert app._offset > 0
            assert app._saw_delta is True

    @pytest.mark.asyncio
    async def test_tick_follow_paused_skips(self, tmp_path: Path) -> None:
        events = [
            {"event_type": "chatter.delta", "payload": {"text": "hi"}},
        ]
        f = _write_events(tmp_path, events)
        app = _make_app(f, follow=True)
        async with app.run_test(size=(120, 40)):
            app.paused = True
            app._tick_follow()
            assert app._offset == 0

    @pytest.mark.asyncio
    async def test_tick_follow_missing_file(self, tmp_path: Path) -> None:
        app = _make_app(tmp_path / "nope.jsonl", follow=True)
        async with app.run_test(size=(120, 40)):
            app._tick_follow()
            assert app._offset == 0

    @pytest.mark.asyncio
    async def test_tick_follow_with_live_source_skips_chatter(self, tmp_path: Path) -> None:
        events = [
            {"event_type": "chatter.delta", "payload": {"text": "hi"}},
            {"event_type": "chatter.tool", "payload": {"name": "Bash", "text": "echo"}},
            {"event_type": "model.profile_changed", "payload": {"model": "opus"}},
        ]
        f = _write_events(tmp_path, events)
        live = BufferingStreamUi()
        app = _make_app(f, follow=True, live_source=live)
        async with app.run_test(size=(120, 40)):
            app._tick_follow()
            assert app.state.model == "opus"


class TestStreamAppTickLive:
    @pytest.mark.asyncio
    async def test_tick_live_processes_prompts_deltas_assistants(self, tmp_path: Path) -> None:
        f = _write_events(tmp_path, [])
        live = BufferingStreamUi()
        app = _make_app(f, follow=True, live_source=live)
        async with app.run_test(size=(120, 40)):
            live.on_prompt("hello")
            live.on_delta("world", turn_id="t1", seq=1)
            live.on_assistant("done")
            app._tick_live()
            assert live.prompts == []
            assert live.deltas == []
            assert live.assistants == []

    @pytest.mark.asyncio
    async def test_tick_live_paused_skips(self, tmp_path: Path) -> None:
        f = _write_events(tmp_path, [])
        live = BufferingStreamUi()
        app = _make_app(f, follow=True, live_source=live)
        async with app.run_test(size=(120, 40)):
            live.on_prompt("hello")
            app.paused = True
            app._tick_live()
            assert len(live.prompts) == 1

    @pytest.mark.asyncio
    async def test_tick_live_no_source_returns(self, tmp_path: Path) -> None:
        f = _write_events(tmp_path, [])
        app = _make_app(f, follow=True)
        async with app.run_test(size=(120, 40)):
            app._tick_live()


class TestStreamAppTickReplay:
    @pytest.mark.asyncio
    async def test_tick_replay_advances(self, tmp_path: Path) -> None:
        events = [
            {"event_type": "chatter.prompt", "payload": {"text": "go"}},
            {"event_type": "chatter.delta", "payload": {"text": "hi"}},
        ]
        f = _write_events(tmp_path, events)
        app = _make_app(f, replay=True, follow=False)
        async with app.run_test(size=(120, 40)):
            app._load_all()
            app._tick_replay()
            assert app._replay_index == 1

    @pytest.mark.asyncio
    async def test_tick_replay_paused_skips(self, tmp_path: Path) -> None:
        events = [
            {"event_type": "chatter.delta", "payload": {"text": "hi"}},
        ]
        f = _write_events(tmp_path, events)
        app = _make_app(f, replay=True, follow=False)
        async with app.run_test(size=(120, 40)):
            app._load_all()
            app.paused = True
            app._tick_replay()
            assert app._replay_index == 0

    @pytest.mark.asyncio
    async def test_tick_replay_not_playing_skips(self, tmp_path: Path) -> None:
        events = [
            {"event_type": "chatter.delta", "payload": {"text": "hi"}},
        ]
        f = _write_events(tmp_path, events)
        app = _make_app(f, replay=True, follow=False)
        # _playing defaults True, and mounting schedules a real 0.05s
        # interval calling _tick_replay -- set it False before run_test()
        # mounts the app, or that timer can race the assertion below under
        # load and advance _replay_index before this test's own manual call.
        app._playing = False
        async with app.run_test(size=(120, 40)):
            app._load_all()
            app._tick_replay()
            assert app._replay_index == 0

    @pytest.mark.asyncio
    async def test_tick_replay_at_end(self, tmp_path: Path) -> None:
        events = [
            {"event_type": "chatter.delta", "payload": {"text": "hi"}},
        ]
        f = _write_events(tmp_path, events)
        app = _make_app(f, replay=True, follow=False)
        async with app.run_test(size=(120, 40)):
            app._load_all()
            app._replay_index = 1
            app._tick_replay()
            assert app._replay_index == 1

    @pytest.mark.asyncio
    async def test_tick_replay_speed_zero(self, tmp_path: Path) -> None:
        events = [{"event_type": "chatter.delta", "payload": {"text": f"t{i}"}} for i in range(30)]
        f = _write_events(tmp_path, events)
        app = _make_app(f, replay=True, follow=False, speed=0)
        async with app.run_test(size=(120, 40)):
            app._load_all()
            app._tick_replay()
            assert app._replay_index == 20


class TestStreamAppActions:
    @pytest.mark.asyncio
    async def test_toggle_pause(self, tmp_path: Path) -> None:
        f = _write_events(tmp_path, [])
        app = _make_app(f, follow=True)
        async with app.run_test(size=(120, 40)):
            assert app.paused is False
            app.action_toggle_pause()
            assert app.paused is True
            app.action_toggle_pause()
            assert app.paused is False

    @pytest.mark.asyncio
    async def test_toggle_play_replay_mode(self, tmp_path: Path) -> None:
        f = _write_events(tmp_path, [])
        app = _make_app(f, replay=True, follow=False)
        async with app.run_test(size=(120, 40)):
            assert app._playing is True
            app.action_toggle_play()
            assert app._playing is False
            app.action_toggle_play()
            assert app._playing is True

    @pytest.mark.asyncio
    async def test_toggle_play_follow_mode(self, tmp_path: Path) -> None:
        f = _write_events(tmp_path, [])
        app = _make_app(f, follow=True)
        async with app.run_test(size=(120, 40)):
            app.action_toggle_play()
            assert app.paused is True

    @pytest.mark.asyncio
    async def test_prev_turn_not_replay(self, tmp_path: Path) -> None:
        f = _write_events(tmp_path, [])
        app = _make_app(f, follow=True)
        async with app.run_test(size=(120, 40)):
            app.action_prev_turn()

    @pytest.mark.asyncio
    async def test_next_turn_not_replay(self, tmp_path: Path) -> None:
        f = _write_events(tmp_path, [])
        app = _make_app(f, follow=True)
        async with app.run_test(size=(120, 40)):
            app.action_next_turn()

    @pytest.mark.asyncio
    async def test_prev_turn_replay(self, tmp_path: Path) -> None:
        events = [
            {"event_type": "chatter.prompt", "payload": {"text": "first"}},
            {"event_type": "chatter.delta", "payload": {"text": "a"}},
            {"event_type": "chatter.prompt", "payload": {"text": "second"}},
            {"event_type": "chatter.delta", "payload": {"text": "b"}},
        ]
        f = _write_events(tmp_path, events)
        app = _make_app(f, replay=True, follow=False)
        async with app.run_test(size=(120, 40)):
            app._load_all()
            app._replay_index = 3
            app.action_prev_turn()
            assert app._replay_index == 1

    @pytest.mark.asyncio
    async def test_next_turn_replay(self, tmp_path: Path) -> None:
        events = [
            {"event_type": "chatter.prompt", "payload": {"text": "first"}},
            {"event_type": "chatter.delta", "payload": {"text": "a"}},
            {"event_type": "chatter.prompt", "payload": {"text": "second"}},
            {"event_type": "chatter.delta", "payload": {"text": "b"}},
        ]
        f = _write_events(tmp_path, events)
        app = _make_app(f, replay=True, follow=False)
        async with app.run_test(size=(120, 40)):
            app._load_all()
            app._replay_index = 0
            app.action_next_turn()
            assert app._replay_index == 1

    @pytest.mark.asyncio
    async def test_next_turn_at_last_turn(self, tmp_path: Path) -> None:
        events = [
            {"event_type": "chatter.prompt", "payload": {"text": "only"}},
            {"event_type": "chatter.delta", "payload": {"text": "x"}},
        ]
        f = _write_events(tmp_path, events)
        app = _make_app(f, replay=True, follow=False)
        async with app.run_test(size=(120, 40)):
            app._load_all()
            app._replay_index = 2
            app.action_next_turn()
            assert app._replay_index == 2


class TestStreamAppThinking:
    @pytest.mark.asyncio
    async def test_set_thinking_on_off(self, tmp_path: Path) -> None:
        f = _write_events(tmp_path, [])
        app = _make_app(f, follow=False)
        async with app.run_test(size=(120, 40)):
            app._set_thinking(True)
            assert app._thinking is True
            bar = app.query_one("#thinking-bar")
            # Static has no public `.renderable`; the content set by update()
            # is read back through render().
            assert "thinking" in str(bar.render()).lower()

            app._set_thinking(False)
            assert app._thinking is False

    @pytest.mark.asyncio
    async def test_tick_thinking_cycles(self, tmp_path: Path) -> None:
        f = _write_events(tmp_path, [])
        app = _make_app(f, follow=False)
        async with app.run_test(size=(120, 40)):
            app._set_thinking(True)
            frames = []
            for _ in range(4):
                app._tick_thinking()
                frames.append(app._thinking_frame)
            assert frames == [1, 2, 0, 1]

    @pytest.mark.asyncio
    async def test_tick_thinking_inactive_noop(self, tmp_path: Path) -> None:
        f = _write_events(tmp_path, [])
        app = _make_app(f, follow=False)
        async with app.run_test(size=(120, 40)):
            app._tick_thinking()
            assert app._thinking_frame == 0


class TestStreamAppApplyChatUpdate:
    @pytest.mark.asyncio
    async def test_apply_with_clear(self, tmp_path: Path) -> None:
        f = _write_events(tmp_path, [])
        app = _make_app(f, follow=False)
        async with app.run_test(size=(120, 40)):
            from claudeloop.infrastructure.stream_ui.app import ChatUpdate

            update = ChatUpdate(
                clear=True,
                assistant_lines=["new content"],
                tool_lines=["tool: info"],
                saw_delta=True,
                header_dirty=True,
            )
            app._apply_chat_update(update)
            assert app._saw_delta is True

    @pytest.mark.asyncio
    async def test_apply_prompt_starts_thinking(self, tmp_path: Path) -> None:
        f = _write_events(tmp_path, [])
        app = _make_app(f, follow=False)
        async with app.run_test(size=(120, 40)):
            from claudeloop.infrastructure.stream_ui.app import ChatUpdate

            update = ChatUpdate(
                assistant_lines=["prompt text"],
                saw_delta=False,
                header_dirty=True,
            )
            app._saw_delta = False
            app._apply_chat_update(update)
            assert app._thinking is True
