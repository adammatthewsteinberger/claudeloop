"""Completion verdicts — was the whole task finished, or just this turn?

Primary source is the structured-output verdict the model returns per turn
(ClaudeAgentOptions.output_format). A legacy substring marker is retained as a
fallback for when structured output isn't available on a given model/config.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_DONE_MARKER = "CLAUDELOOP_TASK_FULLY_COMPLETE"


@dataclass(frozen=True, slots=True)
class Done:
    summary: str = ""


@dataclass(frozen=True, slots=True)
class Continue:
    remaining_work: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Blocked:
    reason: str


CompletionVerdict = Done | Continue | Blocked


@dataclass(frozen=True, slots=True)
class StructuredVerdict:
    """Mirrors the JSON schema handed to the model via output_format:
    {"complete": bool, "remaining_work": [str], "blocked_on": str|null, "summary": str}
    """

    complete: bool
    remaining_work: tuple[str, ...] = ()
    blocked_on: str | None = None
    summary: str = ""


def evaluate(
    *,
    structured: StructuredVerdict | None,
    output_text: str,
    done_marker: str = DEFAULT_DONE_MARKER,
) -> CompletionVerdict:
    """Decide what a single turn's outcome means for the overall task.

    Precedence: a structured verdict is authoritative when present. Only when it is
    absent do we fall back to substring-matching the legacy marker in raw text.
    """
    if structured is not None:
        if structured.blocked_on:
            return Blocked(reason=structured.blocked_on)
        if structured.complete:
            return Done(summary=structured.summary)
        return Continue(remaining_work=structured.remaining_work)

    if done_marker in output_text:
        return Done(summary="")
    return Continue(remaining_work=())
