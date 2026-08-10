from __future__ import annotations

from pathlib import Path

import typer

from autoclaude import bootstrap
from autoclaude.application.usecases.resume_session import (
    resolve_most_recent,
    resume_explicit,
)
from autoclaude.cli.asyncio import async_command
from autoclaude.cli.render import render_session_warning
from autoclaude.domain.errors import InvalidSessionSelectorError
from autoclaude.infrastructure.config import load_config
from autoclaude.infrastructure.logging import configure_logging


def resume(
    session_id: str | None = typer.Option(
        None, "--session-id", help="Resume this specific session id"
    ),
    max_turns: int | None = typer.Option(None, "--max-turns"),
    max_dollars: float | None = typer.Option(None, "--max-dollars"),
    model: str | None = typer.Option(
        None, "--model", help="Claude model id to use for this run, e.g. claude-haiku-4-5"
    ),
    log_level: str = typer.Option("INFO", "--log-level"),
    log_file: Path | None = typer.Option(None, "--log-file"),
) -> None:
    """Resume a Claude Code session and run it autonomously to completion.
    With --session-id, resumes that specific session. Without it, auto-selects
    the most recently modified session for the current directory and prints a
    warning banner naming exactly which one before doing anything."""
    _resume(
        session_id=session_id,
        max_turns=max_turns,
        max_dollars=max_dollars,
        model=model,
        log_level=log_level,
        log_file=log_file,
    )


@async_command
async def _resume(
    *,
    session_id: str | None,
    max_turns: int | None,
    max_dollars: float | None,
    model: str | None,
    log_level: str,
    log_file: Path | None,
) -> None:
    cwd = Path.cwd()
    configure_logging(log_file=log_file, level=log_level)

    resolved_id = session_id
    if resolved_id is None:
        catalog = bootstrap.build_session_catalog()
        try:
            ref = resolve_most_recent(catalog, str(cwd))
        except InvalidSessionSelectorError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=1) from exc
        typer.echo(render_session_warning(ref, str(cwd)), err=True)
        resolved_id = ref.session_id

    config = load_config(
        cwd=cwd,
        cli_overrides={
            "max_turns": max_turns,
            "max_dollars": max_dollars,
            "model": model,
            "log_level": log_level,
        },
    )
    context = bootstrap.build_runner(
        cwd=cwd, config=config, session_id=resolved_id, resume=resolved_id, log_file=log_file
    )
    result = await resume_explicit(context.runner)

    if not result.success:
        typer.echo(f"Run failed: {result.reason}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Done: {result.reason}")
