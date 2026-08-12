from __future__ import annotations

from pathlib import Path

import typer

from claudeloop import bootstrap_ops


def status(
    run_id: str | None = typer.Option(None, "--run-id"),
) -> None:
    """Show status for the active (or specified) run."""
    cwd = Path.cwd()
    try:
        info = bootstrap_ops.run_status(cwd, run_id)
    except FileNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    for key, value in info.items():
        typer.echo(f"{key}: {value}")
