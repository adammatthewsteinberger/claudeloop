from __future__ import annotations

from pathlib import Path

import typer

from claudeloop import bootstrap_ops


def stop(
    run_id: str | None = typer.Option(None, "--run-id", help="Target run id"),
) -> None:
    """Request a soft stop of the active (or specified) run.

    The runner finishes the current turn or aborts a wait, writes
    stop-summary.md, and exits."""
    cwd = Path.cwd()
    try:
        result = bootstrap_ops.enqueue_stop(cwd, run_id)
    except FileNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Stop requested for run {result.run_id}")
