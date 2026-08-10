"""The Typer root app and console-script entry point.

Registered in pyproject.toml as:
    [project.scripts]
    claudeloop = "claudeloop.cli.app:main"
"""

from __future__ import annotations

import typer

from claudeloop import __version__
from claudeloop.bootstrap import build_api_click_group
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


@app.command(
    "api",
    help="Generated 1:1 Anthropic SDK REST surface — run `claudeloop api <resource> ...`.",
    add_help_option=False,
)
def api_stub() -> None:
    """Show the generated API command tree."""
    build_api_click_group()(["--help"])


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
    import sys

    import click

    if len(sys.argv) > 1 and sys.argv[1] == "api":
        group = build_api_click_group()
        try:
            group.main(args=sys.argv[2:], prog_name="claudeloop api", standalone_mode=True)
        except click.exceptions.Exit as exc:
            code = 0 if exc.exit_code is None else exc.exit_code
            raise SystemExit(code) from exc
        return 0
    app(prog_name="claudeloop")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
