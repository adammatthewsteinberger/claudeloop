"""ClaudeSDKClient-backed AgentGateway and CapacityProbe.

Deliberately uses ClaudeSDKClient (streaming-input mode), never query() —
query() raises a bare Exception after yielding an error ResultMessage and the
process exits non-zero, where ClaudeSDKClient survives to be resumed with
another send_turn(). See
docs/architecture/decisions/0002-agent-sdk-over-subprocess.md."""

from __future__ import annotations

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

from autoclaude.application.dto import TurnOutcome
from autoclaude.infrastructure.agent.options import build_probe_options, build_turn_options
from autoclaude.infrastructure.agent.translate import TurnAccumulator


class ClaudeAgentGateway:
    """One live ClaudeSDKClient session. Connect lazily on first send_turn()
    so constructing the gateway never itself talks to the SDK."""

    def __init__(
        self,
        *,
        cwd: str,
        session_id: str | None = None,
        resume: str | None = None,
        continue_conversation: bool = False,
        max_turns: int | None = None,
        max_budget_usd: float | None = None,
        retry_watchdog: bool = False,
        model: str | None = None,
    ) -> None:
        self._cwd = cwd
        self._session_id = session_id
        self._resume = resume
        self._continue_conversation = continue_conversation
        self._max_turns = max_turns
        self._max_budget_usd = max_budget_usd
        self._retry_watchdog = retry_watchdog
        self._model = model
        self._client: ClaudeSDKClient | None = None

    def _options(self) -> ClaudeAgentOptions:
        return build_turn_options(
            cwd=self._cwd,
            session_id=self._session_id,
            resume=self._resume,
            continue_conversation=self._continue_conversation,
            max_turns=self._max_turns,
            max_budget_usd=self._max_budget_usd,
            retry_watchdog=self._retry_watchdog,
            model=self._model,
        )

    async def _ensure_connected(self) -> ClaudeSDKClient:
        if self._client is None:
            self._client = ClaudeSDKClient(options=self._options())
            await self._client.connect()
            # First send is a fresh/resumed session; subsequent sends continue
            # the same live connection — resume/continue_conversation should
            # not be re-applied on turn two or the SDK would treat it as a
            # second resume request.
            self._resume = None
            self._continue_conversation = False
        return self._client

    async def send_turn(self, prompt_text: str) -> TurnOutcome:
        client = await self._ensure_connected()
        await client.query(prompt_text)
        accumulator = TurnAccumulator()
        async for message in client.receive_response():
            accumulator.feed(message)
        return accumulator.build()

    async def close(self) -> None:
        if self._client is not None:
            await self._client.disconnect()
            self._client = None


class ClaudeCapacityProbe:
    """A one-token, tool-free, transcript-free turn used purely to re-check
    capacity while WAITING. Opens and closes its own throwaway client per
    probe — the whole point is that it's cheap and leaves nothing behind."""

    def __init__(self, *, cwd: str, session_id: str | None = None) -> None:
        self._cwd = cwd
        self._session_id = session_id

    async def probe(self) -> TurnOutcome:
        options = build_probe_options(cwd=self._cwd, resume=self._session_id)
        client = ClaudeSDKClient(options=options)
        await client.connect()
        try:
            await client.query("Reply with the single word OK and nothing else.")
            accumulator = TurnAccumulator()
            async for message in client.receive_response():
                accumulator.feed(message)
            return accumulator.build()
        finally:
            await client.disconnect()
