"""SessionLock — advisory file lock preventing two claudeloop runners from
driving the same Claude Code session concurrently. Advisory only (an `flock`
on a marker file): it protects against two claudeloop invocations racing,
not against a session also being driven interactively at the same time."""

from __future__ import annotations

import errno
import os
from pathlib import Path


class FileSessionLock:
    def __init__(self, directory: Path) -> None:
        self._directory = directory
        self._directory.mkdir(parents=True, exist_ok=True)
        self._held: dict[str, int] = {}

    def _path(self, session_id: str) -> Path:
        return self._directory / f"{session_id}.lock"

    def acquire(self, session_id: str) -> bool:
        path = self._path(session_id)
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        except OSError as exc:  # pragma: no cover - platform-dependent errno path
            if exc.errno != errno.EEXIST:
                raise
            return False
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        self._held[session_id] = fd
        return True

    def release(self, session_id: str) -> None:
        self._held.pop(session_id, None)
        path = self._path(session_id)
        if path.is_file():
            path.unlink()
