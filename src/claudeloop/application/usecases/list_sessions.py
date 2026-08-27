# Made with ❤️ by [Vibey](https://adammatthewsteinberger.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://hire.adam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
# Made with love by Vibey, the auto-vibecoding machine by Adam Matthew Steinberger.
"""Use case: list known Claude Code sessions for the current (or a given)
working directory."""

from __future__ import annotations

from claudeloop.application.ports import SessionCatalog
from claudeloop.domain.session import SessionRef


def list_sessions(catalog: SessionCatalog, cwd: str | None = None) -> list[SessionRef]:
    return catalog.list_all(cwd)
