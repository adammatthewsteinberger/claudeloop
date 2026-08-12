from __future__ import annotations

from pathlib import Path

from claudeloop.domain.control import (
    PromptNowCommand,
    SetPresetCommand,
    StopCommand,
    stop_outranks,
)
from claudeloop.domain.stop_summary import StopSummaryInput, render_stop_summary
from claudeloop.infrastructure.control import FileRunControl
from claudeloop.infrastructure.git_savepoints import GitSavePointStore
from claudeloop.infrastructure.lock import FileSessionLock
from claudeloop.infrastructure.rundir import RunDirectory, resolve_run_directory, runs_root_for


def test_stop_outranks_prompts() -> None:
    cmds = stop_outranks([PromptNowCommand(text="x"), StopCommand(), PromptNowCommand(text="y")])
    assert cmds == [StopCommand()]


def test_file_run_control_roundtrip(tmp_path: Path) -> None:
    control = FileRunControl(tmp_path / "inbox")
    control.enqueue(StopCommand())
    control.enqueue(PromptNowCommand(text="hello"))
    # Stop was enqueued first but stop_outranks collapses when both present
    polled = control.poll()
    assert polled == [StopCommand()]


def test_file_run_control_preset_roundtrip(tmp_path: Path) -> None:
    control = FileRunControl(tmp_path / "inbox")
    control.enqueue(SetPresetCommand(preset="high"))
    polled = control.poll()
    assert polled == [SetPresetCommand(preset="high")]


def test_run_directory_create_and_resolve(tmp_path: Path) -> None:
    cwd = tmp_path / "proj"
    cwd.mkdir()
    directory = RunDirectory.create(runs_root_for(cwd), cwd=cwd)
    assert directory.meta_path.is_file()
    resolved = resolve_run_directory(cwd, directory.read_meta().run_id)
    assert resolved.root == directory.root


def test_session_lock_acquire_release(tmp_path: Path) -> None:
    lock = FileSessionLock(tmp_path / "locks")
    assert lock.acquire("sess-1") is True
    assert lock.acquire("sess-1") is False
    lock.release("sess-1")
    assert lock.acquire("sess-1") is True
    lock.release("sess-1")


def test_git_savepoints_create_list_unwind(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    import subprocess

    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    (repo / "a.txt").write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "add", "a.txt"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)

    index = tmp_path / "savepoints.jsonl"
    store = GitSavePointStore(cwd=repo, index_path=index)
    run_id = "run1"
    (repo / "a.txt").write_text("two\n", encoding="utf-8")
    p1 = store.create(run_id=run_id, label="t1", message="first")
    assert p1 is not None
    (repo / "a.txt").write_text("three\n", encoding="utf-8")
    p2 = store.create(run_id=run_id, label="t2", message="second")
    assert p2 is not None
    points = store.list_points(run_id)
    assert len(points) == 2
    result = store.unwind(run_id=run_id, to="1", backup=True)
    assert result.to.n == 1
    assert result.backup_ref is not None
    assert (repo / "a.txt").read_text(encoding="utf-8") == "two\n"


def test_render_stop_summary_includes_sections() -> None:
    md = render_stop_summary(
        StopSummaryInput(
            run_id="r1",
            session_id="s1",
            reason="stopped by operator",
            turns_spent=2,
            dollars_spent=0.5,
            last_summary="did stuff",
            remaining_plan_items=("item a",),
            remaining_work=("more",),
            git_changes="abc commit",
            latest_savepoint="#1",
            events_path="/tmp/events.jsonl",
            resume_hint="resume please",
        )
    )
    assert "stopped by operator" in md
    assert "item a" in md
    assert "resume please" in md
