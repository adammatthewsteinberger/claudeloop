from __future__ import annotations

from pathlib import Path

import typer

from claudeloop import bootstrap_ops


def wind_down(
    run_id: str | None = typer.Option(None, "--run-id", help="Target run id"),
    reason: str = typer.Option("operator", "--reason", help="Recorded in handoff.json"),
) -> None:
    """Ask the active (or specified) run to hand off at its next natural break.

    Softer than `stop`: the turn in flight finishes first, so the handoff
    artifacts describe a consistent point rather than a half-completed one. The
    run writes runs/<id>/handoff.json and exits 75, which is how a supervisor
    tells "resume me elsewhere" from "this failed".

    Use `stop` instead when you want it to end now.
    """
    cwd = Path.cwd()
    try:
        result = bootstrap_ops.enqueue_wind_down(cwd, run_id, reason=reason)
    except FileNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Wind-down requested for run {result.run_id}")
