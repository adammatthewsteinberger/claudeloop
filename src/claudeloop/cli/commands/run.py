from __future__ import annotations

from pathlib import Path

import typer

from claudeloop import bootstrap
from claudeloop.application.usecases.run_plan import run_from_plan_file
from claudeloop.cli.asyncio import async_command
from claudeloop.domain.errors import InvalidPlanError
from claudeloop.infrastructure.config import load_config
from claudeloop.infrastructure.logging import configure_logging


def run(
    plan_file: Path = typer.Argument(
        ..., exists=True, readable=True, help="Markdown plan file to seed a fresh session with"
    ),
    max_turns: int | None = typer.Option(None, "--max-turns"),
    max_dollars: float | None = typer.Option(None, "--max-dollars"),
    max_wait_seconds: float | None = typer.Option(None, "--max-wait"),
    model: str | None = typer.Option(
        None, "--model", help="Claude model id to use for this run, e.g. claude-haiku-4-5"
    ),
    log_level: str = typer.Option("INFO", "--log-level"),
    log_file: Path | None = typer.Option(None, "--log-file"),
) -> None:
    """Seed a brand-new Claude Code session from PLAN_FILE and run it
    autonomously to completion — across turns, across rate-limit windows,
    across a credits top-up — never blocking on a human. See
    docs/guides/autonomous-runs.md."""
    _run(
        plan_file=plan_file,
        max_turns=max_turns,
        max_dollars=max_dollars,
        max_wait_seconds=max_wait_seconds,
        model=model,
        log_level=log_level,
        log_file=log_file,
    )


@async_command
async def _run(
    *,
    plan_file: Path,
    max_turns: int | None,
    max_dollars: float | None,
    max_wait_seconds: float | None,
    model: str | None,
    log_level: str,
    log_file: Path | None,
) -> None:
    cwd = Path.cwd()
    configure_logging(log_file=log_file, level=log_level)
    config = load_config(
        cwd=cwd,
        cli_overrides={
            "max_turns": max_turns,
            "max_dollars": max_dollars,
            "max_wait_seconds": max_wait_seconds,
            "model": model,
            "log_level": log_level,
        },
    )
    context = bootstrap.build_runner(cwd=cwd, config=config, log_file=log_file)
    try:
        result = await run_from_plan_file(context.runner, plan_file)
    except InvalidPlanError as exc:
        typer.echo(f"Invalid plan file: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if not result.success:
        typer.echo(f"Run failed: {result.reason}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Done: {result.reason}")
