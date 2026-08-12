"""Unit tests for AnthropicApiGateway helpers and invoke edge cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from claudeloop.infrastructure.api.gateway import (
    AnthropicApiGateway,
    _collect_paginated,
    _serialize,
)
from claudeloop.infrastructure.api.introspect import DiscoveredMethod


@dataclass
class _Model:
    value: str

    def model_dump(self) -> dict[str, str]:
        return {"value": self.value}


class _Stream:
    def read(self) -> bytes:
        return b"chunk"


class _Page:
    def __init__(
        self, data: list[Any], *, has_more: bool, next_data: list[Any] | None = None
    ) -> None:
        self.data = data
        self.has_more = has_more
        self._next_data = next_data or []

    def get_next_page(self) -> _Page:
        return _Page(self._next_data, has_more=False)


def test_serialize_model_dump_stream_and_nested_containers() -> None:
    assert _serialize(_Model("x")) == {"value": "x"}
    assert _serialize(_Stream()) == {"stream": "<streaming response>"}
    assert _serialize([_Model("a"), {"k": _Model("b")}]) == [
        {"value": "a"},
        {"k": {"value": "b"}},
    ]
    assert _serialize(7) == 7


def test_collect_paginated_honors_max_items_across_pages() -> None:
    first = _Page(["a", "b"], has_more=True, next_data=["c", "d", "e"])
    assert _collect_paginated(first, max_items=3) == ["a", "b", "c"]
    first_again = _Page(["a", "b"], has_more=True, next_data=["c", "d"])
    assert _collect_paginated(first_again, max_items=None) == ["a", "b", "c", "d"]


def test_invoke_rejects_method_outside_provider_surface() -> None:
    gateway = AnthropicApiGateway()
    method = DiscoveredMethod(
        path="models.list",
        resource_path=("models",),
        method_name="list",
        qualname="models.list",
        is_local_helper=False,
        is_list=True,
    )
    with pytest.raises(ValueError, match="not available for provider"):
        gateway.invoke("models.list", provider="bedrock", method=method)
