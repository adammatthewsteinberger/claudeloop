from __future__ import annotations

from pathlib import Path

import typer

from claudeloop import bootstrap_ops


def prompt(
    text: str = typer.Argument(..., help="Prompt text to inject into the loop"),
    now: bool = typer.Option(
        False, "--now", help="Apply at the next operator boundary (immediate)"
    ),
    at_break: bool = typer.Option(
        False,
        "--at-break",
        help="Apply only at a natural break (after Continue, before next send)",
    ),
    run_id: str | None = typer.Option(None, "--run-id"),
) -> None:
    """Inject a new prompt into an active loop session."""
    if now == at_break:
        typer.echo("Specify exactly one of --now or --at-break", err=True)
        raise typer.Exit(code=2)
    cwd = Path.cwd()
    try:
        result = bootstrap_ops.enqueue_prompt(cwd, text, immediate=now, run_id=run_id)
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Enqueued {result.command_type} for run {result.run_id}")
