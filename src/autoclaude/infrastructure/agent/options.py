"""Builds ClaudeAgentOptions for real turns and for the throwaway capacity probe.

Key choices, each tied to an ADR:
- permission_mode="bypassPermissions" — required for autonomy; the Python SDK
  has no dangerously_skip_permissions field, this is its equivalent.
- output_format carries the completion verdict JSON schema (see translate.py).
- CLAUDE_CODE_RETRY_WATCHDOG is NOT set by default — see ADR 0005.
"""

from __future__ import annotations

from claude_agent_sdk import ClaudeAgentOptions

from autoclaude.infrastructure.agent.autonomy import (
    AUTONOMY_SYSTEM_PROMPT_FRAGMENT,
    build_hooks,
    can_use_tool,
)
from autoclaude.infrastructure.agent.translate import COMPLETION_OUTPUT_SCHEMA


def build_turn_options(
    *,
    cwd: str,
    session_id: str | None = None,
    resume: str | None = None,
    continue_conversation: bool = False,
    max_turns: int | None = None,
    max_budget_usd: float | None = None,
    retry_watchdog: bool = False,
) -> ClaudeAgentOptions:
    env: dict[str, str] = {"CLAUDE_CODE_MAX_RETRIES": "10"}
    if retry_watchdog:
        env["CLAUDE_CODE_RETRY_WATCHDOG"] = "1"

    return ClaudeAgentOptions(
        cwd=cwd,
        session_id=session_id,
        resume=resume,
        continue_conversation=continue_conversation,
        permission_mode="bypassPermissions",
        can_use_tool=can_use_tool,
        hooks=build_hooks(),
        system_prompt={
            "type": "preset",
            "preset": "claude_code",
            "append": AUTONOMY_SYSTEM_PROMPT_FRAGMENT,
        },
        output_format={"type": "json_schema", "schema": COMPLETION_OUTPUT_SCHEMA},
        max_turns=max_turns,
        max_budget_usd=max_budget_usd,
        env=env,
    )


def build_probe_options(*, cwd: str, resume: str | None = None) -> ClaudeAgentOptions:
    """Deliberately minimal: one throwaway turn purely to re-check capacity.
    No CLAUDE.md, no tools, no persisted transcript. See
    docs/architecture/decisions/0004-adaptive-waiting-with-probes-not-sleep.md."""
    return ClaudeAgentOptions(
        cwd=cwd,
        resume=resume,
        permission_mode="bypassPermissions",
        can_use_tool=can_use_tool,
        setting_sources=None,
        tools=[],
        max_turns=1,
        extra_args={"no-session-persistence": None},
    )
