"""Git-backed save points under refs/claudeloop/<run_id>/<n>."""

from __future__ import annotations

import json
import subprocess  # nosec B404 — argv lists are fixed git subcommands, never shell=True
from datetime import datetime, timezone
from pathlib import Path

from claudeloop.domain.savepoint import SavePointRef, UnwindResult


class GitSavePointStore:
    def __init__(self, *, cwd: Path, index_path: Path) -> None:
        self._cwd = cwd
        self._index_path = index_path
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._index_path.exists():
            self._index_path.touch()

    def create(self, *, run_id: str, label: str, message: str) -> SavePointRef | None:
        if not self._is_git_repo():
            return None
        self._run(["git", "add", "-A"])
        # Only commit when the index differs from HEAD. Unchanged trees still
        # get a numbered refs/claudeloop/<run_id>/<n> pointing at current HEAD
        # — no empty commits on wait/poll turns.
        has_staged = self._run(["git", "diff", "--cached", "--quiet"], check=False).returncode != 0
        if has_staged:
            self._run(
                [
                    "git",
                    "commit",
                    "--no-verify",
                    "-m",
                    f"claudeloop: savepoint — {message}",
                ],
            )
        sha = self._run(["git", "rev-parse", "HEAD"]).stdout.strip()
        existing = self.list_points(run_id)
        n = (existing[-1].n + 1) if existing else 1
        ref = f"refs/claudeloop/{run_id}/{n}"
        self._run(["git", "update-ref", ref, sha])
        point = SavePointRef(
            n=n,
            ref=ref,
            sha=sha,
            label=label,
            at=datetime.now(timezone.utc),
            plan_item=None,
        )
        self._append_index(point)
        return point

    def list_points(self, run_id: str) -> list[SavePointRef]:
        if not self._index_path.is_file():
            return []
        points: list[SavePointRef] = []
        for line in self._index_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            if data.get("run_id") and data["run_id"] != run_id:
                continue
            points.append(
                SavePointRef(
                    n=int(data["n"]),
                    ref=str(data["ref"]),
                    sha=str(data["sha"]),
                    label=str(data["label"]),
                    at=datetime.fromisoformat(data["at"]),
                    plan_item=data.get("plan_item"),
                )
            )
        return points

    def unwind(self, *, run_id: str, to: str, backup: bool) -> UnwindResult:
        points = self.list_points(run_id)
        target = self._resolve_target(points, to)
        backup_ref: str | None = None
        if backup:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup_ref = f"refs/claudeloop/backup/{run_id}/{stamp}"
            head = self._run(["git", "rev-parse", "HEAD"]).stdout.strip()
            self._run(["git", "update-ref", backup_ref, head])
        self._run(["git", "reset", "--hard", target.sha])
        return UnwindResult(to=target, backup_ref=backup_ref, restored_sha=target.sha)

    def changes_since(self, since_sha: str | None) -> str:
        if not self._is_git_repo():
            return ""
        if since_sha:
            result = self._run(["git", "log", "--oneline", f"{since_sha}..HEAD"], check=False)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        result = self._run(["git", "status", "--short"], check=False)
        return result.stdout.strip() if result.returncode == 0 else ""

    def _append_index(self, point: SavePointRef) -> None:
        # Infer run_id from ref: refs/claudeloop/<run_id>/<n>
        parts = point.ref.split("/")
        run_id = parts[2] if len(parts) >= 4 else ""
        entry = {
            "run_id": run_id,
            "n": point.n,
            "ref": point.ref,
            "sha": point.sha,
            "label": point.label,
            "at": point.at.isoformat(),
            "plan_item": point.plan_item,
        }
        with self._index_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def _resolve_target(self, points: list[SavePointRef], to: str) -> SavePointRef:
        if to.isdigit():
            n = int(to)
            for point in points:
                if point.n == n:
                    return point
            raise ValueError(f"no save point numbered {n}")
        for point in points:
            if point.ref == to or point.sha.startswith(to) or point.label == to:
                return point
        raise ValueError(f"no save point matching {to!r}")

    def _is_git_repo(self) -> bool:
        result = self._run(["git", "rev-parse", "--is-inside-work-tree"], check=False)
        return result.returncode == 0 and result.stdout.strip() == "true"

    def _run(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        # Fixed argv only (git + literal subcommands); cwd is the project worktree.
        return subprocess.run(  # nosec B603
            args,
            cwd=self._cwd,
            check=check,
            capture_output=True,
            text=True,
        )
