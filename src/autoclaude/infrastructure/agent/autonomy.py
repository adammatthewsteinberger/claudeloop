"""The never-block-on-a-human guarantees. See
docs/architecture/decisions/0007-ask-user-question-denied-with-guidance.md and
docs/guides/never-blocking.md for the full mitigation table this implements."""

from __future__ import annotations

from typing import Any

from claude_agent_sdk import (
    HookContext,
    HookMatcher,
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)
from claude_agent_sdk.types import HookInput, HookJSONOutput

_ASK_USER_QUESTION_DENY_MESSAGE = (
    "Running autonomously, no user available to answer — choose the option you "
    "would recommend, note the assumption you're making, and proceed. Do not "
    "wait for a response."
)

AUTONOMY_SYSTEM_PROMPT_FRAGMENT = (
    "You are running autonomously and unattended. Nobody is watching this "
    "session in real time and nobody can answer a question mid-task. Never end "
    "a turn by asking 'Shall I proceed?' or waiting for confirmation on a "
    "reversible action that follows from the task — just do it. If you would "
    "normally ask a clarifying question, make the most reasonable assumption, "
    "state it plainly, and continue."
)


async def can_use_tool(
    tool_name: str,
    tool_input: dict[str, Any],
    context: ToolPermissionContext,
) -> PermissionResultAllow | PermissionResultDeny:
    """Defensive callback: never awaits input, and specifically denies
    AskUserQuestion with guidance rather than fabricating an answer — see the
    ADR above for why a denial beats a synthesized choice."""
    del context  # unused — every path below is context-independent by design
    if tool_name == "AskUserQuestion":
        return PermissionResultDeny(message=_ASK_USER_QUESTION_DENY_MESSAGE, interrupt=False)
    if tool_name == "ExitPlanMode":
        return PermissionResultAllow(updated_input=tool_input)
    return PermissionResultAllow(updated_input=tool_input)


async def _auto_allow_permission_request(
    input_data: HookInput,
    tool_use_id: str | None,
    context: HookContext,
) -> HookJSONOutput:
    del input_data, tool_use_id, context
    return {}


async def _log_notification(
    input_data: HookInput,
    tool_use_id: str | None,
    context: HookContext,
) -> HookJSONOutput:
    del tool_use_id, context
    # Intentionally a no-op beyond returning an empty decision: Notification
    # hooks must never block. Actual logging happens via the AuditLog port at
    # the call site that constructs these hooks (infrastructure/agent/options.py),
    # not here, so this module stays free of an AuditLog dependency.
    del input_data
    return {}


def build_hooks() -> dict[Any, list[HookMatcher]]:
    # dict[Any, ...] rather than the SDK's own HookEvent-literal-keyed type:
    # that type isn't exported as a standalone name we can annotate against
    # without repeating its ten-member Literal union here. mypy still checks
    # the keys used below are valid at the ClaudeAgentOptions(hooks=...) call
    # site in options.py.
    return {
        "PermissionRequest": [HookMatcher(hooks=[_auto_allow_permission_request])],
        "Notification": [HookMatcher(hooks=[_log_notification])],
    }
