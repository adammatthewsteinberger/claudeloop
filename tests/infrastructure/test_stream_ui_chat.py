"""Stream UI chat panel: continuous log, full prompts, no per-turn wipe."""

from __future__ import annotations

from claudeloop.infrastructure.stream_ui import BufferingStreamUi
from claudeloop.infrastructure.stream_ui.app import chat_update_for_record


def test_buffering_stream_ui_queues_full_prompts_without_wiping_history() -> None:
    ui = BufferingStreamUi()
    ui.on_prompt("first prompt " + ("x" * 600))
    ui.on_delta("hello", turn_id="t1", seq=1)
    ui.on_turn_boundary(turn_id="t2", attempt=2)
    ui.on_prompt("second prompt")
    ui.on_assistant("done")
    assert len(ui.prompts) == 2
    assert ui.prompts[0].startswith("first prompt ")
    assert len(ui.prompts[0]) > 512
    assert ui.prompts[1] == "second prompt"
    assert ui.assistants == ["done"]
    # Continuous chat: turn boundary must not erase streamed assistant text.
    assert "hello" in ui.state.assistant


def test_chat_update_appends_prompt_without_clearing() -> None:
    update = chat_update_for_record(
        {
            "event_type": "chatter.prompt",
            "payload": {"text": "full prompt body", "preview": "full"},
        }
    )
    assert update.clear is False
    assert "full prompt body" in "".join(update.assistant_lines)
    assert "prompt" in "".join(update.assistant_lines).lower()


def test_chat_update_skips_assistant_when_deltas_already_streamed() -> None:
    first = chat_update_for_record(
        {"event_type": "chatter.delta", "payload": {"text": "partial"}},
        saw_delta=False,
    )
    assert first.saw_delta is True
    assert first.assistant_lines == ["partial"]
    second = chat_update_for_record(
        {"event_type": "chatter.assistant", "payload": {"text": "partial full"}},
        saw_delta=True,
    )
    assert second.assistant_lines == []


def test_chat_update_prefers_full_text_over_preview() -> None:
    update = chat_update_for_record(
        {
            "event_type": "chatter.prompt",
            "payload": {"text": "COMPLETE_PROMPT_BODY", "preview": "COMP"},
        }
    )
    joined = "".join(update.assistant_lines)
    assert "COMPLETE_PROMPT_BODY" in joined
    assert joined.count("COMP") == 0 or "COMPLETE_PROMPT_BODY" in joined
