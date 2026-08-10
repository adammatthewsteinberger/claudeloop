"""structlog configuration: JSON to file, human-readable to console, and a
redaction processor scrubbing secret-shaped fields before anything is written
anywhere. This matters more than usual for claudeloop — see SECURITY.md — both
because debug logging is a stated requirement and because the (M4) REST
surface includes vaults and credentials."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import structlog

_REDACTED_KEYS = frozenset(
    {
        "api_key",
        "authorization_token",
        "access_token",
        "refresh_token",
        "client_secret",
        "secret_value",
        "authorization",
        "x-api-key",
    }
)
_REDACTED_VALUE = "***REDACTED***"


def _redact_processor(
    _logger: object, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    for key in list(event_dict):
        if key.lower() in _REDACTED_KEYS:
            event_dict[key] = _REDACTED_VALUE
    return event_dict


def configure_logging(*, log_file: Path | None, level: str = "INFO") -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=getattr(logging, level.upper(), logging.INFO),
    )

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _redact_processor,
    ]

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_processors = [*processors, structlog.processors.JSONRenderer()]
        file_logger_factory = structlog.WriteLoggerFactory(
            file=log_file.open("a", encoding="utf-8")
        )
        structlog.configure(
            processors=file_processors,
            logger_factory=file_logger_factory,
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, level.upper(), logging.INFO)
            ),
        )
    else:
        console_processors = [*processors, structlog.dev.ConsoleRenderer()]
        structlog.configure(
            processors=console_processors,
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, level.upper(), logging.INFO)
            ),
        )


def get_logger(**initial_context: Any) -> structlog.stdlib.BoundLogger:
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(**initial_context)
    return logger
