"""Tests for infrastructure/resources/adapter.py — ResourcePortAdapter."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from claudeloop.infrastructure.resources.adapter import ResourcePortAdapter
from claudeloop.infrastructure.resources.store import RunResourceStore


def _make_store(tmp_path: Path) -> RunResourceStore:
    root = tmp_path / "run" / "resources"
    (tmp_path / "run" / "artifacts").mkdir(parents=True)
    (tmp_path / "run" / "memories").mkdir(parents=True)
    store = RunResourceStore(root)
    return store


class TestResourcePortAdapter:
    def test_init_marks_dirty(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        adapter = ResourcePortAdapter(store)
        assert adapter.dirty is True

    def test_store_property(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        adapter = ResourcePortAdapter(store)
        assert adapter.store is store

    def test_gateway_payload_clears_dirty(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        adapter = ResourcePortAdapter(store)
        assert adapter.dirty is True
        payload = adapter.gateway_payload()
        assert adapter.dirty is False
        assert isinstance(payload, dict)

    def test_gateway_payload_shape(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        adapter = ResourcePortAdapter(store)
        payload = adapter.gateway_payload()
        assert "add_dirs" in payload
        assert "skills" in payload
        assert "plugins" in payload
        assert "mcp_servers" in payload
        assert "system_prompt_append" in payload
        assert "allowed_tools" in payload

    def test_set_permission_mode(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        adapter = ResourcePortAdapter(store)
        adapter.set_permission_mode("manual")
        snap = store.snapshot()
        assert snap.permission_mode == "manual"

    def test_set_cwd(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        adapter = ResourcePortAdapter(store)
        adapter.set_cwd(str(tmp_path))
        snap = store.snapshot()
        assert snap.cwd is not None

    def test_mutate_attachment_add(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        adapter = ResourcePortAdapter(store)
        src = tmp_path / "doc.txt"
        src.write_text("content", encoding="utf-8")
        result = adapter.apply_mutate(action="add", kind="attachment", value=str(src))
        assert "path" in result

    def test_mutate_attachment_rm(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        adapter = ResourcePortAdapter(store)
        src = tmp_path / "doc.txt"
        src.write_text("content", encoding="utf-8")
        adapter.apply_mutate(action="add", kind="attachment", value=str(src))
        result = adapter.apply_mutate(action="rm", kind="attachment", value=str(src))
        assert "removed" in result

    def test_mutate_folder_add_rm(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        adapter = ResourcePortAdapter(store)
        result = adapter.apply_mutate(action="add", kind="folder", value="/tmp/test")
        assert result["folder"] == "/tmp/test"
        result = adapter.apply_mutate(action="rm", kind="folder", value="/tmp/test")
        assert result["removed"] == "/tmp/test"

    def test_mutate_skill_add_rm(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        adapter = ResourcePortAdapter(store)
        result = adapter.apply_mutate(action="add", kind="skill", value="s1")
        assert result["skill"] == "s1"
        result = adapter.apply_mutate(action="rm", kind="skill", value="s1")
        assert result["removed"] == "s1"

    def test_mutate_plugin_add_rm(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        adapter = ResourcePortAdapter(store)
        result = adapter.apply_mutate(action="add", kind="plugin", value="p1")
        assert result["plugin"] == "p1"
        result = adapter.apply_mutate(action="rm", kind="plugin", value="p1")
        assert result["removed"] == "p1"

    def test_mutate_connector_url(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        adapter = ResourcePortAdapter(store)
        result = adapter.apply_mutate(
            action="add", kind="connector", value="http://localhost",
            name="my-conn",
        )
        assert result["connector"] == "my-conn"

    def test_mutate_connector_json(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        adapter = ResourcePortAdapter(store)
        result = adapter.apply_mutate(
            action="set", kind="mcp", value='{"url":"http://x"}',
            name="mc",
        )
        assert result["connector"] == "mc"

    def test_mutate_connector_rm(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        adapter = ResourcePortAdapter(store)
        adapter.apply_mutate(
            action="add", kind="connector", value="http://localhost", name="c1",
        )
        result = adapter.apply_mutate(action="rm", kind="connector", name="c1", value="c1")
        assert result["removed"] == "c1"

    def test_mutate_github_set(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        adapter = ResourcePortAdapter(store)
        result = adapter.apply_mutate(action="set", kind="github", value="owner/repo")
        assert result["owner"] == "owner"
        assert result["repo"] == "repo"

    def test_mutate_github_rm(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        adapter = ResourcePortAdapter(store)
        adapter.apply_mutate(action="set", kind="github", value="owner/repo")
        result = adapter.apply_mutate(action="rm", kind="github", value="")
        assert result["cleared"] is True

    def test_mutate_memory_add_rm(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        adapter = ResourcePortAdapter(store)
        result = adapter.apply_mutate(
            action="set", kind="memory", value="remember this", name="note1",
        )
        assert "path" in result
        result = adapter.apply_mutate(action="rm", kind="memory", value="note1", name="note1")
        assert result["removed"] == "note1"

    def test_mutate_web_search_add_rm(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        adapter = ResourcePortAdapter(store)
        result = adapter.apply_mutate(action="add", kind="web-search", value="")
        assert result["web_search"] is True
        result = adapter.apply_mutate(action="rm", kind="web-search", value="")
        assert result["web_search"] is False

    def test_mutate_research_add(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        adapter = ResourcePortAdapter(store)
        result = adapter.apply_mutate(action="add", kind="research", value="how does X?")
        assert "research_path" in result

    def test_mutate_research_status(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        adapter = ResourcePortAdapter(store)
        result = adapter.apply_mutate(action="status", kind="research", value="")
        assert "status" in result

    def test_mutate_unsupported_raises(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        adapter = ResourcePortAdapter(store)
        with pytest.raises(ValueError, match="unsupported"):
            adapter.apply_mutate(action="add", kind="unknown", value="x")

    def test_gateway_payload_with_web_search(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        adapter = ResourcePortAdapter(store)
        adapter.apply_mutate(action="add", kind="web-search", value="")
        payload = adapter.gateway_payload()
        assert "WebSearch" in payload["allowed_tools"]
