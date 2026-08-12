from __future__ import annotations

import pytest

from claudeloop.domain.control import (
    PromptDeferredCommand,
    PromptNowCommand,
    SetEffortCommand,
    SetModelCommand,
    SetPresetCommand,
    StopCommand,
    stop_outranks,
)


def test_stop_alone() -> None:
    assert stop_outranks([StopCommand()]) == [StopCommand()]


def test_latest_prompt_now_wins() -> None:
    result = stop_outranks([PromptNowCommand(text="a"), PromptNowCommand(text="b")])
    assert result == [PromptNowCommand(text="b")]


def test_now_and_deferred_both_kept() -> None:
    result = stop_outranks([PromptDeferredCommand(text="d"), PromptNowCommand(text="n")])
    assert result == [PromptNowCommand(text="n"), PromptDeferredCommand(text="d")]


def test_empty_batch() -> None:
    assert stop_outranks([]) == []


def test_blank_prompts_rejected() -> None:
    with pytest.raises(ValueError):
        PromptNowCommand(text="")
    with pytest.raises(ValueError):
        PromptDeferredCommand(text="   ")


def test_blank_model_rejected() -> None:
    with pytest.raises(ValueError):
        SetModelCommand(model="  ")


def test_profile_commands_latest_wins() -> None:
    result = stop_outranks(
        [
            SetPresetCommand(preset="low"),
            SetPresetCommand(preset="high"),
            SetModelCommand(model="medium"),
            SetEffortCommand(effort="max"),
        ]
    )
    assert result == [
        SetPresetCommand(preset="high"),
        SetModelCommand(model="medium"),
        SetEffortCommand(effort="max"),
    ]
