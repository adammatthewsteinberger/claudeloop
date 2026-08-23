# Made with love by Vibey, the auto-vibecoding machine by Adam Matthew Steinberger.
"""The generated REST surface seam."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ApiGateway(Protocol):
    """Declared now; implemented in M4 alongside the generated REST surface.
    See docs/architecture/decisions/0006-generated-rest-surface-not-hand-written.md."""

    def invoke(self, method_path: str, **kwargs: Any) -> Any: ...
