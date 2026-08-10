"""Configuration precedence: CLI flags > environment variables > config file >
built-in defaults. See docs/getting-started/configuration.md for the full
settings table this backs."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised only on Python 3.10, outside the CI matrix's tested code path here  # noqa: E501
    import tomli as tomllib

_ENV_PREFIX = "AUTOCLAUDE_"


@dataclass(frozen=True, slots=True)
class RunnerConfig:
    max_turns: int | None = None
    max_dollars: float | None = None
    max_attempts: int | None = None
    max_wait_seconds: float | None = None
    credits_probe_interval_seconds: float = 120.0
    credits_probe_ceiling_seconds: float = 600.0
    window_probe_interval_seconds: float = 600.0
    reset_grace_seconds: float = 60.0
    done_marker: str | None = None
    log_level: str = "INFO"
    log_file: str | None = None
    retry_watchdog: bool = False


def _from_env() -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    for f in fields(RunnerConfig):
        env_name = _ENV_PREFIX + f.name.upper()
        raw = os.environ.get(env_name)
        if raw is None:
            continue
        overrides[f.name] = _coerce(raw, f.type)
    return overrides


def _from_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    known = {f.name for f in fields(RunnerConfig)}
    return {k: v for k, v in data.items() if k in known}


def _coerce(raw: str, type_hint: Any) -> Any:
    hint = str(type_hint)
    if "bool" in hint:
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    if "float" in hint:
        return float(raw)
    if "int" in hint:
        return int(raw)
    return raw


def load_config(
    *,
    cwd: Path,
    home: Path | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> RunnerConfig:
    config = RunnerConfig()

    file_overrides: dict[str, Any] = {}
    home_config = (home or Path.home()) / ".config" / "autoclaude" / "config.toml"
    file_overrides.update(_from_file(home_config))
    file_overrides.update(_from_file(cwd / "autoclaude.toml"))
    if file_overrides:
        config = replace(config, **file_overrides)

    env_overrides = _from_env()
    if env_overrides:
        config = replace(config, **env_overrides)

    if cli_overrides:
        cleaned = {k: v for k, v in cli_overrides.items() if v is not None}
        if cleaned:
            config = replace(config, **cleaned)

    return config
