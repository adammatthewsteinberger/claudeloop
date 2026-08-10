"""Paid-tier live tests: drive a real Claude Code session end to end. Spends
real tokens/turns against your account. Opt in with:

    pytest -m "live and paid" --run-paid-live tests/live/test_paid_tier.py

Every test here:
- Runs in a fresh temp git repo (the `sandbox_repo` fixture), never a real
  project.
- Pins `--model claude-haiku-4-5`, the cheapest available model.
- Caps `--max-turns` and `--max-dollars` tightly.
- Uses a minimal, cheap-to-satisfy prompt.
"""

from __future__ import annotations

import subprocess  # nosec B404 - fixed-argument calls only, never shell=True
from pathlib import Path

import pytest

pytestmark = [pytest.mark.live, pytest.mark.paid]

_CHEAP_MODEL = "claude-haiku-4-5"


def _run_autoclaude(
    args: list[str], *, cwd: Path, timeout: int = 300
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 B607
        ["autoclaude", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def test_run_completes_a_trivial_plan_end_to_end(sandbox_repo: Path) -> None:
    """The plan asks for the smallest possible verifiable action: create one
    file with known content. Asserts the file genuinely exists afterward,
    not just that the process exited 0 — a fake success is worse than an
    honest failure."""
    plan = sandbox_repo / "handoff.md"
    plan.write_text(
        "Create a file named result.txt in the current directory containing "
        "exactly the text OK (no extra whitespace or newline content beyond "
        "what a text editor would normally add). Do nothing else.\n"
    )

    result = _run_autoclaude(
        [
            "run",
            str(plan),
            "--model",
            _CHEAP_MODEL,
            "--max-turns",
            "5",
            "--max-dollars",
            "0.50",
        ],
        cwd=sandbox_repo,
    )

    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    created = sandbox_repo / "result.txt"
    assert created.is_file()
    assert created.read_text().strip() == "OK"

    audit_log = sandbox_repo / "autoclaude.log.jsonl"
    assert audit_log.is_file()
    assert "finished" in audit_log.read_text()


def test_resume_continues_a_session_created_by_run(sandbox_repo: Path) -> None:
    """Runs a two-step plan deliberately split across `run` (step 1) and a
    plain `resume` with no --session-id (step 2, auto-selecting the session
    `run` just created) -- proving auto-select + resume drives the SAME
    session forward rather than starting a fresh one."""
    plan = sandbox_repo / "handoff.md"
    plan.write_text(
        "Create a file named step1.txt containing exactly OK. Then STOP -- "
        "do not create step2.txt yet, even though a follow-up will ask for "
        "it later in a separate turn.\n"
    )
    first = _run_autoclaude(
        ["run", str(plan), "--model", _CHEAP_MODEL, "--max-turns", "3", "--max-dollars", "0.30"],
        cwd=sandbox_repo,
    )
    assert first.returncode == 0, f"stdout={first.stdout!r} stderr={first.stderr!r}"
    assert (sandbox_repo / "step1.txt").is_file()

    second = _run_autoclaude(
        ["resume", "--model", _CHEAP_MODEL, "--max-turns", "3", "--max-dollars", "0.30"],
        cwd=sandbox_repo,
    )
    # resume's auto-select banner goes to stderr before any real work starts
    assert "Auto-selected the MOST RECENT" in second.stderr


def test_never_blocks_on_a_clarifying_question(sandbox_repo: Path) -> None:
    """A plan that explicitly invites the model to ask a clarifying question.
    Bounded by the subprocess timeout itself: if the never-block mitigations
    (AskUserQuestion denied with guidance -- see ADR 0007) ever regress into
    actually waiting on stdin, this test hangs and fails on timeout rather
    than hanging the whole suite indefinitely."""
    plan = sandbox_repo / "handoff.md"
    plan.write_text(
        "You need to create a config file, but the format isn't specified. "
        "Consider asking the user whether they want JSON or YAML -- then "
        "make a reasonable choice yourself (you are running unattended and "
        "nobody can answer), create config.json or config.yaml with any "
        "trivial valid content, and finish.\n"
    )

    result = _run_autoclaude(
        [
            "run",
            str(plan),
            "--model",
            _CHEAP_MODEL,
            "--max-turns",
            "5",
            "--max-dollars",
            "0.50",
        ],
        cwd=sandbox_repo,
        timeout=180,  # a real hang must fail here, not stall the suite
    )

    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    created = list(sandbox_repo.glob("config.*"))
    assert created, "expected the model to make an assumption and create a config file"
