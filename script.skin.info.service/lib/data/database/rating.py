"""Provider response caching for ratings sources."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from lib.data.database._infrastructure import (
    get_db,
    compress_data as _compress_data,
    decompress_data as _decompress_data,
)
from lib.data.database.cache import get_cache_ttl_hours, get_cached_metadata
from lib.data.database.mapping import get_tmdb_id_by_imdb

_RELEASE_DATE_HINT_KEY = "_release_date"


def get_provider_cache(provider: str, media_id: str) -> Optional[dict]:
    """Get cached provider data if not expired based on smart TTL."""
    with get_db() as cursor:
        cursor.execute(
            "SELECT data, release_date, cached_at FROM provider_cache "
            "WHERE provider = ? AND media_id = ?",
            (provider, media_id)
        )
        row = cursor.fetchone()
        if not row:
            return None

        hints = _get_provider_ttl_hints(media_id)
        release_date = row["release_date"]
        if not release_date and hints:
            release_date = hints.pop(_RELEASE_DATE_HINT_KEY, None)
        ttl_hours = get_cache_ttl_hours(release_date, hints or None)
        cached_at = datetime.fromisoformat(row["cached_at"])
        if datetime.now() - cached_at > timedelta(hours=ttl_hours):
            return None
        return _decompress_data(row["data"])


def _get_provider_ttl_hints(media_id: str) -> Optional[dict]:
    """Try to derive TTL hints from the mapping + metadata cache."""
    if not media_id or not media_id.startswith("tt"):
        return None

    for media_type in ("movie", "tvshow"):
        tmdb_id = get_tmdb_id_by_imdb(media_id, media_type)
        if tmdb_id:
            meta = get_cached_metadata(media_type, tmdb_id)
            if not meta:
                return None
            hints: dict = {}
            status = meta.get("status") or ""
            if status:
                hints["status"] = status
            release = meta.get("release_date") or meta.get("first_air_date")
            if release:
                hints[_RELEASE_DATE_HINT_KEY] = release
            return hints
    return None


def save_provider_cache(provider: str, media_id: str, data: dict,
                        release_date: Optional[str] = None) -> None:
    """Upsert a compressed provider response into `provider_cache`."""
    with get_db() as cursor:
        cursor.execute(
            "\n            INSERT OR REPLACE INTO provider_cache "
            "(provider, media_id, data, release_date, cached_at)\n"
            "            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)\n            ",
            (provider, media_id, _compress_data(data), release_date)
        )
