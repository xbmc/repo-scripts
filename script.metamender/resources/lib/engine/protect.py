"""Provenance rule for writing onto NFO-managed items.

Values that came from an NFO file are never changed. Metamender may fill an
empty field and keep refreshing a value it wrote itself, recognised by the
fingerprint it stored when it wrote it.

Logging:
    Logger: none (pure functions)
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from resources.lib.engine.textrules import is_empty_text

# Kodi stores ratings as 32-bit floats, so 7.28 comes back as
# 7.28000020980835. Two decimals absorb that round trip and still distinguish
# every rating a provider returns.
_FLOAT_PLACES = 2


def _canonical(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, _FLOAT_PLACES)
    if isinstance(value, dict):
        return {str(k): _canonical(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    return value


def fingerprint(value: Any) -> str:
    """Stable digest of a field value (sha1 of canonical JSON).

    Dict keys are sorted, floats are rounded to two decimals, and non-ASCII
    text is kept as UTF-8, so the digest does not depend on the Python
    version, dict ordering or Kodi's float round trip.
    """
    text = json.dumps(
        _canonical(value), sort_keys=True, separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def is_blank(value: Any) -> bool:
    """Empty, zero, a placeholder text, or a container of only such values:
    a value Kodi holds that says nothing."""
    if value is None:
        return True
    if isinstance(value, str):
        return is_empty_text(value)
    if isinstance(value, (list, tuple, dict)):
        items = value.values() if isinstance(value, dict) else value
        return all(is_blank(v) for v in items)
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value == 0
    return False


def may_write(protected: bool, current: Any, written_value: str | None) -> bool:
    """May metamender overwrite ``current``?

    Always for an unprotected value. A protected one (any field of an
    NFO-managed item, or a language field in a folder with no configured
    language) only when it is empty or a placeholder, or still equals what
    metamender last wrote (``written_value`` is that value's fingerprint).
    Anything else came from the NFO, the scraper or the user and is left
    alone.
    """
    if not protected:
        return True
    if is_blank(current):
        return True
    return written_value is not None and fingerprint(current) == written_value
