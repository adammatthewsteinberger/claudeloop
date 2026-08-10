"""Unit tests for Anthropic SDK introspection (no credentials)."""

from __future__ import annotations

from claudeloop.infrastructure.api.introspect import (
    LOCAL_HELPER_PATHS,
    discover_surface,
    resolve_callable,
)


def test_discover_surface_includes_core_roots() -> None:
    paths = {m.path for m in discover_surface()}
    assert "messages.create" in paths
    assert "models.list" in paths
    assert "beta.sessions.list" in paths


def test_local_helper_paths_are_marked() -> None:
    by_path = {m.path: m for m in discover_surface()}
    for helper in LOCAL_HELPER_PATHS:
        assert by_path[helper].is_local_helper


def test_resolve_callable_finds_messages_create() -> None:
    method = next(m for m in discover_surface() if m.path == "messages.create")
    fn = resolve_callable(method)
    assert fn.__name__ == "create"
