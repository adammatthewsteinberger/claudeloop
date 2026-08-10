from __future__ import annotations

import typer

from autoclaude import bootstrap
from autoclaude.application.usecases.list_sessions import list_sessions as list_sessions_uc
from autoclaude.cli.render import render_session_list

app = typer.Typer(add_completion=False)


@app.callback(invoke_without_command=True)
def sessions(
    ctx: typer.Context,
    cwd: str | None = typer.Option(
        None, "--cwd", help="Directory to list sessions for (default: current directory)"
    ),
) -> None:
    """List known Claude Code sessions, read-only — never mutates or drives
    a session, just shows what's there."""
    if ctx.invoked_subcommand is not None:
        return
    catalog = bootstrap.build_session_catalog()
    refs = list_sessions_uc(catalog, cwd)
    typer.echo(render_session_list(refs))
