"""Lightweight API helpers with no heavy dependencies.

Importing from this module is cheap; it pulls no API client, database, or HTTP
chain. Helpers that need those should live in their owning API module instead.
"""
from __future__ import annotations

from base64 import b64decode
from typing import Optional


TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"


def decode_key(blob: str) -> str:
    """Decode a built-in provider key."""
    return b64decode(blob).decode("ascii")


def tmdb_image_url(path: Optional[str], size: str = "original") -> str:
    """Build a TMDB CDN URL for `path` at `size`. Empty string if path is missing.

    Common sizes: w185 (small thumb), w500 (poster), w780 (fanart), original (full).
    `path` is the leading-slash form TMDB returns (e.g. `/abc.jpg`).
    """
    if not path:
        return ""
    return f"{TMDB_IMAGE_BASE}/{size}{path}"


def is_valid_tmdb_id(tmdb_id: Optional[str]) -> bool:
    """Check if a TMDB ID looks valid (numeric only, reasonable length)."""
    if not tmdb_id:
        return False
    return str(tmdb_id).isdigit() and len(str(tmdb_id)) <= 10
