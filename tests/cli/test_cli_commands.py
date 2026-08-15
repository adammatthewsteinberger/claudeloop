"""Tests for CLI command modules — operator control commands.

Tests the thin Typer wrappers around bootstrap_ops, ensuring correct argument
routing and error handling without needing a live run.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from claudeloop.cli.app import app

runner = CliRunner()
_ENV = {"NO_COLOR": "1", "TERM": "dumb", "FORCE_COLOR": "0"}


def _run_dir(tmp_path: Path):
    from claudeloop.infrastructure.rundir import RunDirectory, runs_root_for

    return RunDirectory.create(runs_root_for(tmp_path), cwd=tmp_path)


class TestStopCommand:
    def test_stop_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(app, ["stop", "--run-id", run_id], env=_ENV)
        assert result.exit_code == 0
        assert "Stop requested" in result.output

    def test_stop_no_run_found(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["stop", "--run-id", "nonexistent"], env=_ENV)
        assert result.exit_code == 1


class TestPromptCommand:
    def test_prompt_needs_now_or_at_break(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["prompt", "hello"], env=_ENV)
        assert result.exit_code == 2
        assert "Specify exactly one" in result.output

    def test_prompt_both_now_and_at_break(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["prompt", "hello", "--now", "--at-break"], env=_ENV,
        )
        assert result.exit_code == 2

    def test_prompt_now_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["prompt", "hello", "--now", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0
        assert "Enqueued" in result.output

    def test_prompt_at_break(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["prompt", "hello", "--at-break", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0


class TestModelCommand:
    def test_model_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(app, ["model", "high", "--run-id", run_id], env=_ENV)
        assert result.exit_code == 0
        assert "set_model" in result.output

    def test_model_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["model", "high", "--run-id", "x"], env=_ENV)
        assert result.exit_code == 1


class TestEffortCommand:
    def test_effort_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(app, ["effort", "max", "--run-id", run_id], env=_ENV)
        assert result.exit_code == 0
        assert "set_effort" in result.output


class TestPresetCommand:
    def test_preset_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(app, ["preset", "high", "--run-id", run_id], env=_ENV)
        assert result.exit_code == 0
        assert "set_preset" in result.output


class TestSlashCommand:
    def test_slash_without_prefix_fails(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["slash", "no-prefix"], env=_ENV)
        assert result.exit_code == 2
        assert "must start with '/'" in result.output

    def test_slash_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["slash", "/help", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0
        assert "slash" in result.output.lower()


class TestWindDownCommand:
    def test_wind_down_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["wind-down", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0
        assert "Wind-down requested" in result.output

    def test_wind_down_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["wind-down", "--run-id", "nope"], env=_ENV)
        assert result.exit_code == 1


class TestLogsCommand:
    def test_logs_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["logs", "--run-id", "missing"], env=_ENV)
        assert result.exit_code == 1


class TestStatusCommand:
    def test_status_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(app, ["status", "--run-id", run_id], env=_ENV)
        assert result.exit_code == 0

    def test_status_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["status", "--run-id", "nope"], env=_ENV)
        assert result.exit_code == 1


class TestResetCommand:
    def test_reset_without_yes_fails(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["reset"], env=_ENV)
        assert result.exit_code == 1

    def test_reset_with_yes(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        # _run_dir defaults to status="active" with this test process's own
        # (live) pid, which is exactly the case reset_project_state refuses --
        # a --yes reset never overrides a live run. Mark it finished first.
        directory = _run_dir(tmp_path)
        directory.update_meta(status="finished")
        result = runner.invoke(app, ["reset", "--yes"], env=_ENV)
        assert result.exit_code == 0
        assert "Removed" in result.output


class TestRunsCommand:
    def test_runs_no_runs(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["runs"], env=_ENV)
        assert result.exit_code == 0
        assert "No runs" in result.output

    def test_runs_with_runs(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(app, ["runs"], env=_ENV)
        assert result.exit_code == 0
        assert run_id in result.output


class TestSessionsCommand:
    def test_sessions_no_sessions(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["sessions"], env=_ENV)
        assert result.exit_code == 0


class TestSavepointsCommand:
    def test_savepoints_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["savepoints", "--run-id", "nope"], env=_ENV)
        assert result.exit_code == 1

    def test_savepoints_empty(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(app, ["savepoints", "--run-id", run_id], env=_ENV)
        assert result.exit_code == 0
        assert "No save points" in result.output


class TestUnwindCommand:
    def test_unwind_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["unwind", "--to", "1", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1


class TestChatCommands:
    def test_chat_list_empty(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["chat", "list"], env=_ENV)
        assert result.exit_code == 0
        assert "No chats" in result.output

    def test_chat_show(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["chat", "show", "test-session"], env=_ENV)
        assert result.exit_code == 0

    def test_chat_rename(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["chat", "rename", "s1", "new-name"], env=_ENV)
        assert result.exit_code == 0
        assert "Renamed" in result.output

    def test_chat_delete_missing(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["chat", "delete", "nonexistent"], env=_ENV)
        assert result.exit_code == 1

    def test_chat_pin_unpin(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["chat", "pin", "s1"], env=_ENV)
        assert result.exit_code == 0
        result = runner.invoke(app, ["chat", "unpin", "s1"], env=_ENV)
        assert result.exit_code == 0

    def test_chat_unread_read(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["chat", "unread", "s1"], env=_ENV)
        assert result.exit_code == 0
        result = runner.invoke(app, ["chat", "read", "s1"], env=_ENV)
        assert result.exit_code == 0

    def test_chat_project(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["chat", "project", "s1", "my-project"], env=_ENV,
        )
        assert result.exit_code == 0
        assert "project" in result.output.lower()


class TestConnectorCommands:
    def test_connector_add_url(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app,
            ["connector", "add", "myconn", "http://localhost", "--run-id", run_id],
            env=_ENV,
        )
        assert result.exit_code == 0

    def test_connector_add_invalid_json(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app,
            ["connector", "add", "myconn", "{bad", "--run-id", run_id],
            env=_ENV,
        )
        assert result.exit_code == 2

    def test_connector_rm(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app,
            ["connector", "rm", "myconn", "--run-id", run_id],
            env=_ENV,
        )
        assert result.exit_code == 0

    def test_connector_list_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["connector", "list", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1


class TestToolCommands:
    def test_tool_approve_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["tool", "approve", "req-1", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1

    def test_tool_deny_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["tool", "deny", "req-1", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1


class TestWatchCommand:
    def test_watch_sys_stdout_isatty(self) -> None:
        from claudeloop.cli.commands.watch import sys_stdout_isatty

        result = sys_stdout_isatty()
        assert isinstance(result, bool)


class TestVoiceCommands:
    def test_voice_start(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["voice", "start"], env=_ENV)
        assert result.exit_code == 1

    def test_voice_stop(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["voice", "stop"], env=_ENV)
        assert result.exit_code == 1

    def test_voice_status(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["voice", "status"], env=_ENV)
        assert result.exit_code == 0
        assert "not running" in result.output.lower()

    def test_speak_no_tts(self, tmp_path: Path, monkeypatch) -> None:
        import shutil as _shutil

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(_shutil, "which", lambda _: None)
        result = runner.invoke(app, ["speak", "hello"], env=_ENV)
        assert result.exit_code == 1


class TestAttachCommand:
    def test_attach_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        f = tmp_path / "note.txt"
        f.write_text("hi", encoding="utf-8")
        result = runner.invoke(
            app, ["attach", str(f), "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1

    def test_unattach_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["unattach", "note.txt", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1


class TestFolderCommands:
    def test_folder_add_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["folder", "add", str(tmp_path), "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1

    def test_folder_rm_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["folder", "rm", str(tmp_path), "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1


class TestSkillCommands:
    def test_skill_add_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["skill", "add", "s1", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1

    def test_skill_rm_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["skill", "rm", "s1", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1


class TestPluginCommands:
    def test_plugin_add_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["plugin", "add", "p1", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1

    def test_plugin_rm_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["plugin", "rm", "p1", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1


class TestMemoryCommands:
    def test_memory_list_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["memory", "list", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1

    def test_memory_get_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["memory", "get", "note1", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1

    def test_memory_set_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["memory", "set", "note1", "body", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1

    def test_memory_rm_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["memory", "rm", "note1", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1


class TestGithubCommands:
    def test_github_add_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["github", "add", "owner/repo", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1

    def test_github_import_issue_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["github", "import-issue", "owner/repo#1", "--run-id", "nope"],
            env=_ENV,
        )
        assert result.exit_code == 1


class TestArtifactCommands:
    def test_artifact_list_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["artifact", "list", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1

    def test_artifact_get_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["artifact", "get", "thing", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1

    def test_artifact_rm_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["artifact", "rm", "thing", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1


class TestResearchCommands:
    def test_research_start_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["research", "start", "query", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1

    def test_research_status_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["research", "status", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1


class TestWebSearchCommand:
    def test_web_search_enable_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["web-search", "enable", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1

    def test_web_search_disable_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["web-search", "disable", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1


class TestPermissionModeCommand:
    def test_permission_mode_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["permission-mode", "manual", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1


class TestCwdCommand:
    def test_cwd_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["cwd", str(tmp_path), "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1


class TestResponseCommand:
    def test_response_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["response", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code != 0


class TestDoctorCommand:
    def test_doctor_help(self) -> None:
        result = runner.invoke(app, ["doctor", "--help"], env=_ENV)
        assert result.exit_code == 0
        assert "Pre-flight" in result.output or "Usage" in result.output


class TestResumeCommand:
    def test_resume_help(self) -> None:
        result = runner.invoke(app, ["resume", "--help"], env=_ENV)
        assert result.exit_code == 0
        assert "session" in result.output.lower()


class TestRunCommand:
    def test_run_help(self) -> None:
        result = runner.invoke(app, ["run", "--help"], env=_ENV)
        assert result.exit_code == 0
        assert "plan" in result.output.lower() or "Usage" in result.output

    def test_run_nonexistent_plan(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["run", "nonexistent.md"], env=_ENV)
        assert result.exit_code == 2


class TestConnectorAddSuccess:
    def test_connector_add_json(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app,
            ["connector", "add", "myconn", '{"url":"http://x"}', "--run-id", run_id],
            env=_ENV,
        )
        assert result.exit_code == 0
        assert "Queued" in result.output

    def test_connector_list_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["connector", "list", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0


class TestResponseSubcommands:
    def test_response_copy_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["response", "copy", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1

    def test_response_good_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["response", "good", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1

    def test_response_bad_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["response", "bad", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1

    def test_response_retry_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["response", "retry", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1

    def test_response_good_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["response", "good", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0
        assert "good feedback" in result.output.lower()

    def test_response_bad_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["response", "bad", "--note", "needs fix", "--run-id", run_id],
            env=_ENV,
        )
        assert result.exit_code == 0
        assert "bad feedback" in result.output.lower()

    def test_response_retry_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["response", "retry", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0
        assert "retry" in result.output.lower()


class TestLogsSuccess:
    def test_logs_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(app, ["logs", "--run-id", run_id], env=_ENV)
        assert result.exit_code == 0


class TestWatchCommand:
    def test_watch_no_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["watch", "--no-follow", "--run-id", "nope"], env=_ENV,
        )
        assert result.exit_code == 1

    def test_watch_help(self) -> None:
        result = runner.invoke(app, ["watch", "--help"], env=_ENV)
        assert result.exit_code == 0
        assert "follow" in result.output.lower()


class TestToolCommandsSuccess:
    def test_tool_approve_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["tool", "approve", "req-1", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0

    def test_tool_deny_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["tool", "deny", "req-1", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0


class TestChatListWithData:
    def test_chat_list_with_pinned(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["chat", "pin", "s1"], env=_ENV)
        result = runner.invoke(app, ["chat", "list"], env=_ENV)
        assert result.exit_code == 0

    def test_chat_share(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["chat", "share", "test-session"], env=_ENV)
        assert result.exit_code == 0


class TestAttachSuccess:
    def test_attach_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        f = tmp_path / "note.txt"
        f.write_text("content", encoding="utf-8")
        result = runner.invoke(
            app, ["attach", str(f), "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0

    def test_unattach_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["unattach", "note.txt", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0


class TestFolderSuccess:
    def test_folder_add_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["folder", "add", str(tmp_path), "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0

    def test_folder_rm_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["folder", "rm", str(tmp_path), "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0


class TestSkillSuccess:
    def test_skill_add_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["skill", "add", "my-skill", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0

    def test_skill_rm_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["skill", "rm", "my-skill", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0


class TestPluginSuccess:
    def test_plugin_add_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["plugin", "add", "my-plugin", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0

    def test_plugin_rm_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["plugin", "rm", "my-plugin", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0


class TestMemorySuccess:
    def test_memory_set_and_list(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["memory", "set", "prefs", "be concise", "--run-id", run_id],
            env=_ENV,
        )
        assert result.exit_code == 0
        result = runner.invoke(
            app, ["memory", "list", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0
        assert "prefs" in result.output

    def test_memory_get_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        runner.invoke(
            app, ["memory", "set", "note1", "body text", "--run-id", run_id],
            env=_ENV,
        )
        result = runner.invoke(
            app, ["memory", "get", "note1", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0
        assert "body text" in result.output

    def test_memory_rm_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        runner.invoke(
            app, ["memory", "set", "note1", "body", "--run-id", run_id],
            env=_ENV,
        )
        result = runner.invoke(
            app, ["memory", "rm", "note1", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0


class TestGithubSuccess:
    def test_github_add_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["github", "add", "owner/repo", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0


class TestArtifactSuccess:
    def test_artifact_list_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["artifact", "list", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0


class TestResearchSuccess:
    def test_research_start_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["research", "start", "my query", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0

    def test_research_status_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["research", "status", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0


class TestWebSearchSuccess:
    def test_web_search_enable_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["web-search", "enable", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0

    def test_web_search_disable_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["web-search", "disable", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0


class TestPermissionModeSuccess:
    def test_permission_mode_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["permission-mode", "plan", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0

    def test_permission_mode_manual(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["permission-mode", "manual", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0


class TestCwdSuccess:
    def test_cwd_success(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["cwd", str(tmp_path), "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0


class TestSavepointsSuccess:
    def test_savepoints_list(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        directory = _run_dir(tmp_path)
        run_id = directory.read_meta().run_id
        result = runner.invoke(
            app, ["savepoints", "--run-id", run_id], env=_ENV,
        )
        assert result.exit_code == 0
