"""Use case: pre-flight checks before starting a long unattended run.

Deliberately checks BEFORE a run starts, not during — an MCP OAuth prompt or a
missing `claude` binary discovered three hours into an unattended run is much
worse than the same failure at `autoclaude doctor` time. See
docs/architecture/decisions/0007-ask-user-question-denied-with-guidance.md for
why MCP OAuth specifically can never be mitigated mid-run."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class DoctorCheck:
    name: str
    passed: bool
    detail: str


class DoctorEnvironment(Protocol):
    """What doctor needs from the outside world — kept separate from the
    larger AgentGateway/SessionCatalog ports so `doctor` stays cheap to run
    and doesn't require a live SDK connection."""

    def find_claude_cli(self) -> str | None: ...
    def claude_cli_version(self, path: str) -> str | None: ...
    def is_authenticated(self) -> bool: ...
    def configured_mcp_servers(self) -> list[str]: ...


def run_doctor(env: DoctorEnvironment, *, cwd: Path) -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []

    cli_path = env.find_claude_cli()
    if cli_path is None:
        checks.append(
            DoctorCheck(
                name="claude-cli",
                passed=False,
                detail="`claude` not found on PATH. Install Claude Code first.",
            )
        )
    else:
        version = env.claude_cli_version(cli_path)
        checks.append(
            DoctorCheck(
                name="claude-cli",
                passed=version is not None,
                detail=f"found at {cli_path} ({version or 'version unknown'})",
            )
        )

    authed = env.is_authenticated()
    checks.append(
        DoctorCheck(
            name="authentication",
            passed=authed,
            detail="credentials present" if authed else "no credentials found",
        )
    )

    mcp_servers = env.configured_mcp_servers()
    if mcp_servers:
        checks.append(
            DoctorCheck(
                name="mcp-servers",
                passed=False,
                detail=(
                    f"{len(mcp_servers)} MCP server(s) configured ({', '.join(mcp_servers)}) — "
                    "MCP OAuth cannot complete unattended; verify these are already "
                    "authorized before starting a long run."
                ),
            )
        )
    else:
        checks.append(DoctorCheck(name="mcp-servers", passed=True, detail="none configured"))

    is_git_repo = (cwd / ".git").is_dir()
    checks.append(
        DoctorCheck(
            name="working-directory",
            passed=is_git_repo,
            detail=(
                f"{cwd} is a git repository"
                if is_git_repo
                else f"{cwd} is NOT a git repository — bypassing permissions here is riskier"
            ),
        )
    )

    return checks


def all_passed(checks: list[DoctorCheck]) -> bool:
    return all(c.passed for c in checks)
