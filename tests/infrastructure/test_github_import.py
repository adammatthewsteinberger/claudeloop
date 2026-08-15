"""Tests for infrastructure/github_import.py — parsing and import helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from claudeloop.infrastructure.github_import import (
    ImportedIssue,
    materialize_issue_attachment,
    parse_issue_ref,
    parse_repo_ref,
)


class TestParseIssueRef:
    def test_valid_ref(self) -> None:
        owner, repo, num = parse_issue_ref("owner/repo#42")
        assert owner == "owner"
        assert repo == "repo"
        assert num == 42

    def test_whitespace_stripped(self) -> None:
        owner, repo, num = parse_issue_ref("  owner/repo#1  ")
        assert owner == "owner"
        assert num == 1

    def test_no_hash_raises(self) -> None:
        with pytest.raises(ValueError, match="OWNER/REPO#N"):
            parse_issue_ref("owner/repo")

    def test_no_slash_raises(self) -> None:
        with pytest.raises(ValueError, match="OWNER/REPO#N"):
            parse_issue_ref("repo#42")

    def test_empty_owner_raises(self) -> None:
        with pytest.raises(ValueError, match="OWNER/REPO#N"):
            parse_issue_ref("/repo#42")

    def test_empty_repo_raises(self) -> None:
        with pytest.raises(ValueError, match="OWNER/REPO#N"):
            parse_issue_ref("owner/#42")

    def test_non_numeric_issue_raises(self) -> None:
        with pytest.raises(ValueError, match="OWNER/REPO#N"):
            parse_issue_ref("owner/repo#abc")


class TestParseRepoRef:
    def test_simple_repo(self) -> None:
        owner, repo, ref = parse_repo_ref("owner/repo")
        assert owner == "owner"
        assert repo == "repo"
        assert ref is None

    def test_repo_with_ref(self) -> None:
        owner, repo, ref = parse_repo_ref("owner/repo@main")
        assert owner == "owner"
        assert repo == "repo"
        assert ref == "main"

    def test_whitespace_stripped(self) -> None:
        owner, repo, ref = parse_repo_ref("  owner/repo@v1  ")
        assert owner == "owner"
        assert ref == "v1"

    def test_no_slash_raises(self) -> None:
        with pytest.raises(ValueError, match="OWNER/REPO"):
            parse_repo_ref("noslash")

    def test_empty_owner_raises(self) -> None:
        with pytest.raises(ValueError, match="OWNER/REPO"):
            parse_repo_ref("/repo")

    def test_empty_repo_raises(self) -> None:
        with pytest.raises(ValueError, match="OWNER/REPO"):
            parse_repo_ref("owner/")

    def test_empty_ref_treated_as_none(self) -> None:
        owner, repo, ref = parse_repo_ref("owner/repo@")
        assert ref is None


class TestImportedIssue:
    def test_as_prompt_fragment(self) -> None:
        issue = ImportedIssue(
            owner="o",
            repo="r",
            number=1,
            title="Fix bug",
            body="The fix",
            url="https://example.com",
        )
        fragment = issue.as_prompt_fragment()
        assert "o/r#1" in fragment
        assert "Fix bug" in fragment
        assert "The fix" in fragment
        assert "https://example.com" in fragment


class TestMaterializeIssueAttachment:
    def test_writes_markdown(self, tmp_path: Path) -> None:
        issue = ImportedIssue(
            owner="owner",
            repo="repo",
            number=42,
            title="Title",
            body="Body text",
            url="https://github.com/owner/repo/issues/42",
        )
        result = materialize_issue_attachment(issue, tmp_path / "attachments")
        assert result.is_file()
        content = result.read_text(encoding="utf-8")
        assert "# Title" in content
        assert "Body text" in content
        assert "https://github.com/owner/repo/issues/42" in content

    def test_creates_directory(self, tmp_path: Path) -> None:
        issue = ImportedIssue(
            owner="o",
            repo="r",
            number=1,
            title="T",
            body="B",
            url="u",
        )
        attachments = tmp_path / "deep" / "attachments"
        materialize_issue_attachment(issue, attachments)
        assert attachments.is_dir()


class TestImportGithubIssue:
    def test_import_via_gh_cli(self) -> None:
        from unittest.mock import MagicMock, patch

        from claudeloop.infrastructure.github_import import import_github_issue

        mock_result = MagicMock()
        mock_result.stdout = (
            '{"title":"Test","body":"Body","html_url":"https://github.com/o/r/issues/1"}'
        )

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            issue = import_github_issue("o/r#1")
            assert issue.title == "Test"
            assert issue.body == "Body"
            assert issue.owner == "o"
            assert issue.repo == "r"
            assert issue.number == 1
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "gh" in args
            assert "repos/o/r/issues/1" in args

    def test_import_fallback_to_api_on_gh_not_found(self) -> None:
        from unittest.mock import patch

        from claudeloop.infrastructure.github_import import import_github_issue

        with (
            patch("subprocess.run", side_effect=FileNotFoundError("gh not found")),
            patch("claudeloop.infrastructure.github_import._fetch_issue_api") as mock_fetch,
        ):
            mock_fetch.return_value = {
                "title": "API Title",
                "body": "API Body",
                "html_url": "https://github.com/owner/repo/issues/42",
            }
            issue = import_github_issue("owner/repo#42")
            assert issue.title == "API Title"
            assert issue.body == "API Body"
            mock_fetch.assert_called_once_with("owner", "repo", 42)

    def test_import_fallback_to_api_on_gh_error(self) -> None:
        from subprocess import CalledProcessError
        from unittest.mock import patch

        from claudeloop.infrastructure.github_import import import_github_issue

        with (
            patch(
                "subprocess.run",
                side_effect=CalledProcessError(1, ["gh"], stderr="error"),
            ),
            patch("claudeloop.infrastructure.github_import._fetch_issue_api") as mock_fetch,
        ):
            mock_fetch.return_value = {"title": "T", "body": "B", "html_url": "u"}
            issue = import_github_issue("o/r#1")
            assert issue.title == "T"
            mock_fetch.assert_called_once()
