"""The Typer root app and console-script entry point.

Registered in pyproject.toml as:
    [project.scripts]
    claudeloop = "claudeloop.cli.app:main"
"""

from __future__ import annotations

import typer

from claudeloop import __version__
from claudeloop.cli.commands.doctor import app as doctor_app
from claudeloop.cli.commands.resume import resume
from claudeloop.cli.commands.run import run
from claudeloop.cli.commands.sessions import app as sessions_app

app = typer.Typer(
    name="claudeloop",
    help=(
        "Onion-architected, autonomous Claude Code session runner — never "
        "blocks on a human, distinguishes rate limits from exhausted credits, "
        "and resumes safely across usage windows."
    ),
    add_completion=False,
    no_args_is_help=True,
)

app.command(name="run")(run)
app.command(name="resume")(resume)
app.add_typer(sessions_app, name="sessions")
app.add_typer(doctor_app, name="doctor")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"claudeloop {__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the installed claudeloop version and exit.",
    ),
) -> None:
    del version  # handled entirely by the eager callback above


def main() -> int:
    app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
