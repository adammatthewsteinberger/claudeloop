"""Tests for infrastructure/github_import.py — parsing and import helpers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

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
            owner="o", repo="r", number=1,
            title="Fix bug", body="The fix", url="https://example.com",
        )
        fragment = issue.as_prompt_fragment()
        assert "o/r#1" in fragment
        assert "Fix bug" in fragment
        assert "The fix" in fragment
        assert "https://example.com" in fragment


class TestMaterializeIssueAttachment:
    def test_writes_markdown(self, tmp_path: Path) -> None:
        issue = ImportedIssue(
            owner="owner", repo="repo", number=42,
            title="Title", body="Body text",
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
            owner="o", repo="r", number=1,
            title="T", body="B", url="u",
        )
        attachments = tmp_path / "deep" / "attachments"
        materialize_issue_attachment(issue, attachments)
        assert attachments.is_dir()
