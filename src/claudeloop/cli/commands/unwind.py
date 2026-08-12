from __future__ import annotations

from pathlib import Path

import typer

from claudeloop import bootstrap_ops


def unwind(
    to: str = typer.Option(..., "--to", help="Save point number, sha prefix, or label"),
    run_id: str | None = typer.Option(None, "--run-id"),
    backup: bool = typer.Option(
        True, "--backup/--no-backup", help="Create a backup ref before resetting"
    ),
) -> None:
    """Unwind the worktree to a prior save point (refuses while a run is active)."""
    cwd = Path.cwd()
    try:
        result = bootstrap_ops.unwind_savepoint(cwd, to, backup=backup, run_id=run_id)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Restored save point #{result['to_n']} ({result['restored_sha'][:12]})")
    if result["backup_ref"]:
        typer.echo(f"Backup ref: {result['backup_ref']}")
