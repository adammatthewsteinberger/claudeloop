from __future__ import annotations

from pathlib import Path

import typer

from claudeloop import bootstrap_ops


def logs(
    run_id: str | None = typer.Option(None, "--run-id"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow like tail -f"),
    chatter: bool = typer.Option(
        False, "--chatter", help="Only show chatter.* events (includes trace_id/turn_id)"
    ),
) -> None:
    """Tail the per-run events.jsonl stream (redacted, realtime)."""
    cwd = Path.cwd()
    try:
        bootstrap_ops.tail_events(cwd, run_id=run_id, follow=follow, chatter_only=chatter)
    except FileNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    except KeyboardInterrupt:  # pragma: no cover
        raise typer.Exit(code=0) from None
