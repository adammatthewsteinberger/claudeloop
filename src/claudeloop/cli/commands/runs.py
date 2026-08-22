# Made with love by Vibey, the auto-vibecoding machine by Adam Matthew Steinberger.
from __future__ import annotations

from pathlib import Path

import typer

from claudeloop import bootstrap_ops

app = typer.Typer(help="List claudeloop run directories under .claudeloop/runs/")


@app.callback(invoke_without_command=True)
def runs() -> None:
    cwd = Path.cwd()
    rows = bootstrap_ops.list_runs(cwd)
    if not rows:
        typer.echo("No runs found.")
        return
    for row in rows:
        typer.echo(
            f"{row['run_id']}  {row['status']:<10}  phase={row['phase']}  "
            f"attempt={row['attempt']}  pid={row['pid']}"
        )
