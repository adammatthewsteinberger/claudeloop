"""Tests for infrastructure/agent/gateway.py — ClaudeAgentGateway + ClaudeCapacityProbe.

Uses mocked ClaudeSDKClient to test gateway logic without a live SDK connection.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claudeloop.infrastructure.agent.gateway import (
    ClaudeAgentGateway,
    ClaudeCapacityProbe,
)


def _make_gateway(**kwargs):
    defaults = dict(cwd="/tmp/test")
    defaults.update(kwargs)
    return ClaudeAgentGateway(**defaults)


class TestClaudeAgentGatewayInit:
    def test_defaults(self) -> None:
        gw = _make_gateway()
        assert gw._cwd == "/tmp/test"
        assert gw._client is None
        assert gw._session_id is None
        assert gw._resume is None
        assert gw._model is None
        assert gw._effort is None
        assert gw._add_dirs == []
        assert gw._plugins == []
        assert gw._mcp_servers == {}
        assert gw._allowed_tools == []
        assert gw._delta_seq == 0

    def test_with_all_params(self) -> None:
        gw = _make_gateway(
            session_id="s1",
            resume="r1",
            continue_conversation=True,
            max_turns=10,
            max_budget_usd=5.0,
            retry_watchdog=True,
            model="claude-sonnet",
            effort="high",
            on_event=lambda e: None,
            max_buffer_size=1024,
            include_partial_messages=True,
            add_dirs=["/a", "/b"],
            skills=["sk1"],
            plugins=["p1"],
            mcp_servers={"s": {"url": "http://x"}},
            system_prompt_append="extra",
            allowed_tools=["Bash"],
            tool_approval_timeout=60.0,
        )
        assert gw._session_id == "s1"
        assert gw._resume == "r1"
        assert gw._continue_conversation is True
        assert gw._max_turns == 10
        assert gw._model == "claude-sonnet"
        assert gw._effort == "high"
        assert gw._add_dirs == ["/a", "/b"]
        assert gw._plugins == ["p1"]
        assert gw._mcp_servers == {"s": {"url": "http://x"}}
        assert gw._allowed_tools == ["Bash"]


class TestSetEventListener:
    def test_set_listener(self) -> None:
        gw = _make_gateway()
        fn = lambda e: None
        gw.set_event_listener(fn)
        assert gw._on_event is fn

    def test_set_none(self) -> None:
        gw = _make_gateway(on_event=lambda e: None)
        gw.set_event_listener(None)
        assert gw._on_event is None


class TestResolveToolApproval:
    def test_delegates_to_gate(self) -> None:
        gw = _make_gateway()
        result = gw.resolve_tool_approval("req-1", allow=True)
        assert isinstance(result, bool)


class TestSetProfile:
    @pytest.mark.asyncio
    async def test_no_op_when_same(self) -> None:
        gw = _make_gateway(model="claude-sonnet", effort="high")
        from claudeloop.domain.model_profile import ModelEffortProfile

        profile = ModelEffortProfile(model="claude-sonnet", effort="high")
        gw._client = MagicMock()
        await gw.set_profile(profile)
        # Client should still be set (not reconnected)
        assert gw._client is not None

    @pytest.mark.asyncio
    async def test_reconnects_when_changed(self) -> None:
        gw = _make_gateway(model="claude-sonnet", effort="high")
        from claudeloop.domain.model_profile import ModelEffortProfile

        profile = ModelEffortProfile(model="claude-opus", effort="max")
        mock_client = AsyncMock()
        gw._client = mock_client
        await gw.set_profile(profile)
        assert gw._model == "claude-opus"
        assert gw._effort == "max"
        mock_client.disconnect.assert_awaited_once()
        assert gw._client is None


class TestSetPermissionMode:
    @pytest.mark.asyncio
    async def test_no_op_when_same(self) -> None:
        gw = _make_gateway(permission_mode="bypass")
        gw._client = MagicMock()
        await gw.set_permission_mode("bypass")
        assert gw._client is not None

    @pytest.mark.asyncio
    async def test_reconnects_when_changed(self) -> None:
        gw = _make_gateway(permission_mode="bypass")
        mock_client = AsyncMock()
        gw._client = mock_client
        await gw.set_permission_mode("plan")
        mock_client.disconnect.assert_awaited_once()
        assert gw._client is None


class TestSetCwd:
    @pytest.mark.asyncio
    async def test_no_op_when_same(self) -> None:
        gw = _make_gateway(cwd="/tmp/test")
        gw._client = MagicMock()
        await gw.set_cwd("/tmp/test")
        assert gw._client is not None

    @pytest.mark.asyncio
    async def test_reconnects_when_changed(self) -> None:
        gw = _make_gateway(cwd="/tmp/test")
        mock_client = AsyncMock()
        gw._client = mock_client
        await gw.set_cwd("/tmp/other")
        assert gw._cwd == "/tmp/other"
        mock_client.disconnect.assert_awaited_once()
        assert gw._client is None


class TestSetSessionResources:
    @pytest.mark.asyncio
    async def test_no_change(self) -> None:
        gw = _make_gateway(add_dirs=["/a"], plugins=["p1"])
        gw._client = MagicMock()
        await gw.set_session_resources(add_dirs=["/a"], plugins=["p1"])
        # No reconnect if nothing changed
        assert gw._client is not None

    @pytest.mark.asyncio
    async def test_add_dirs_changed(self) -> None:
        gw = _make_gateway(add_dirs=["/a"])
        mock_client = AsyncMock()
        gw._client = mock_client
        await gw.set_session_resources(add_dirs=["/a", "/b"])
        assert gw._add_dirs == ["/a", "/b"]
        mock_client.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_skills_changed(self) -> None:
        gw = _make_gateway(skills=["s1"])
        mock_client = AsyncMock()
        gw._client = mock_client
        await gw.set_session_resources(skills=["s1", "s2"])
        assert gw._skills == ["s1", "s2"]
        mock_client.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_plugins_changed(self) -> None:
        gw = _make_gateway(plugins=["p1"])
        mock_client = AsyncMock()
        gw._client = mock_client
        await gw.set_session_resources(plugins=["p1", "p2"])
        assert gw._plugins == ["p1", "p2"]
        mock_client.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_mcp_servers_changed(self) -> None:
        gw = _make_gateway()
        mock_client = AsyncMock()
        gw._client = mock_client
        await gw.set_session_resources(mcp_servers={"new": {"url": "http://x"}})
        assert gw._mcp_servers == {"new": {"url": "http://x"}}
        mock_client.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_system_prompt_changed(self) -> None:
        gw = _make_gateway(system_prompt_append="old")
        mock_client = AsyncMock()
        gw._client = mock_client
        await gw.set_session_resources(system_prompt_append="new")
        assert gw._system_prompt_append == "new"
        mock_client.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_allowed_tools_changed(self) -> None:
        gw = _make_gateway(allowed_tools=["Bash"])
        mock_client = AsyncMock()
        gw._client = mock_client
        await gw.set_session_resources(allowed_tools=["Bash", "Read"])
        assert gw._allowed_tools == ["Bash", "Read"]
        mock_client.disconnect.assert_awaited_once()


class TestReconnect:
    @pytest.mark.asyncio
    async def test_reconnect_with_session_id(self) -> None:
        gw = _make_gateway(session_id="s1")
        mock_client = AsyncMock()
        gw._client = mock_client
        await gw._reconnect()
        assert gw._resume == "s1"
        assert gw._continue_conversation is False
        mock_client.disconnect.assert_awaited_once()
        assert gw._client is None

    @pytest.mark.asyncio
    async def test_reconnect_without_session_id(self) -> None:
        gw = _make_gateway()
        mock_client = AsyncMock()
        gw._client = mock_client
        await gw._reconnect()
        assert gw._continue_conversation is True
        mock_client.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reconnect_no_client(self) -> None:
        gw = _make_gateway()
        await gw._reconnect()
        # No error when _client is None


class TestClose:
    @pytest.mark.asyncio
    async def test_close_with_client(self) -> None:
        gw = _make_gateway()
        mock_client = AsyncMock()
        gw._client = mock_client
        await gw.close()
        mock_client.disconnect.assert_awaited_once()
        assert gw._client is None

    @pytest.mark.asyncio
    async def test_close_without_client(self) -> None:
        gw = _make_gateway()
        await gw.close()


class TestSendTurn:
    @pytest.mark.asyncio
    async def test_send_turn_connects_and_returns_outcome(self) -> None:
        from claude_agent_sdk import ResultMessage

        gw = _make_gateway()
        mock_client = AsyncMock()

        result_msg = MagicMock(spec=ResultMessage)
        result_msg.cost_usd = 0.01
        result_msg.duration_ms = 1000
        result_msg.duration_api_ms = 800
        result_msg.is_error = False
        result_msg.session_id = "sess-123"
        result_msg.num_turns = 1
        result_msg.total_cost_usd = 0.01

        async def fake_receive():
            yield result_msg

        mock_client.receive_response = fake_receive
        mock_client.query = AsyncMock()
        mock_client.connect = AsyncMock()

        with patch(
            "claudeloop.infrastructure.agent.gateway.ClaudeSDKClient",
            return_value=mock_client,
        ):
            outcome = await gw.send_turn("hello")

        mock_client.connect.assert_awaited_once()
        mock_client.query.assert_awaited_once_with("hello")
        assert gw._session_id == "sess-123"


class TestEnsureConnected:
    @pytest.mark.asyncio
    async def test_drains_approval_events(self) -> None:
        gw = _make_gateway()
        events_received = []
        gw._on_event = lambda e: events_received.append(e)
        gw._approval.resolve("pre-1", allow=True)

        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        with patch(
            "claudeloop.infrastructure.agent.gateway.ClaudeSDKClient",
            return_value=mock_client,
        ):
            client = await gw._ensure_connected()
        assert client is mock_client

    @pytest.mark.asyncio
    async def test_reuses_existing_client(self) -> None:
        gw = _make_gateway()
        mock_client = AsyncMock()
        gw._client = mock_client
        result = await gw._ensure_connected()
        assert result is mock_client


class TestClaudeCapacityProbe:
    def test_init(self) -> None:
        probe = ClaudeCapacityProbe(cwd="/tmp/test")
        assert probe._cwd == "/tmp/test"
        assert probe._model is None

    def test_set_model(self) -> None:
        probe = ClaudeCapacityProbe(cwd="/tmp/test")
        probe.set_model("claude-sonnet")
        assert probe._model == "claude-sonnet"

    @pytest.mark.asyncio
    async def test_probe_connects_queries_disconnects(self) -> None:
        from claude_agent_sdk import ResultMessage

        probe = ClaudeCapacityProbe(cwd="/tmp/test", model="claude-sonnet")

        result_msg = MagicMock(spec=ResultMessage)
        result_msg.cost_usd = 0.001
        result_msg.duration_ms = 500
        result_msg.duration_api_ms = 400
        result_msg.is_error = False
        result_msg.session_id = "probe-sess"
        result_msg.num_turns = 1
        result_msg.total_cost_usd = 0.001

        mock_client = AsyncMock()

        async def fake_receive():
            yield result_msg

        mock_client.receive_response = fake_receive
        mock_client.query = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()

        with patch(
            "claudeloop.infrastructure.agent.gateway.ClaudeSDKClient",
            return_value=mock_client,
        ):
            outcome = await probe.probe()

        mock_client.connect.assert_awaited_once()
        mock_client.query.assert_awaited_once()
        mock_client.disconnect.assert_awaited_once()
