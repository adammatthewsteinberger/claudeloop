"""Use case: list known Claude Code sessions for the current (or a given)
working directory."""

from __future__ import annotations

from autoclaude.application.ports import SessionCatalog
from autoclaude.domain.session import SessionRef


def list_sessions(catalog: SessionCatalog, cwd: str | None = None) -> list[SessionRef]:
    return catalog.list_all(cwd)
