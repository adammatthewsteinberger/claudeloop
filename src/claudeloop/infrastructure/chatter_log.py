"""Helpers for emitting chatter.* events at the configured verbosity."""

from __future__ import annotations

import json
from typing import Any

from claudeloop.domain.chatter import truncate_chatter


def chatter_payload(
    text: str,
    *,
    mode: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Build a chatter payload for the given mode, or None when off."""
    if mode == "off":
        return None
    if mode == "summary":
        body = truncate_chatter(text, cap_bytes=512)
        payload: dict[str, Any] = {
            "preview": body.text,
            "length": len(text),
            "truncated": body.truncated or len(text) > len(body.text),
        }
    else:
        body = truncate_chatter(text)
        payload = {
            "text": body.text,
            "length": len(text),
            "truncated": body.truncated,
        }
    if extra:
        payload.update(extra)
    return payload


def summarize_tool(name: str, raw: object, *, mode: str) -> dict[str, Any] | None:
    if mode == "off":
        return None
    try:
        rendered = raw if isinstance(raw, str) else json.dumps(raw, default=str)
    except TypeError:
        rendered = repr(raw)
    base = chatter_payload(rendered, mode=mode, extra={"name": name})
    return base
