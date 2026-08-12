"""Pure helpers for chatter field truncation."""

from __future__ import annotations

from dataclasses import dataclass

CHATTER_FIELD_CAP_BYTES = 256 * 1024


@dataclass(frozen=True, slots=True)
class TruncatedText:
    text: str
    truncated: bool


def truncate_chatter(value: str, *, cap_bytes: int = CHATTER_FIELD_CAP_BYTES) -> TruncatedText:
    encoded = value.encode("utf-8")
    if len(encoded) <= cap_bytes:
        return TruncatedText(text=value, truncated=False)
    # Cut on a UTF-8 boundary.
    cut = encoded[:cap_bytes]
    while cut and (cut[-1] & 0xC0) == 0x80:
        cut = cut[:-1]
    return TruncatedText(text=cut.decode("utf-8", errors="ignore"), truncated=True)
