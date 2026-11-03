"""Provider response caching for ratings sources."""
from __future__ import annotations

import time
from typing import Optional, Set, Tuple, Final

from lib.data.database._infrastructure import (
    get_db,
    compress_data as _compress_data,
    decompress_data as _decompress_data,
)
from lib.data.database.cache import get_cache_ttl_hours, get_title_ttl_hours
from lib.data.database.mapping import get_tmdb_id_by_imdb

_NO_PART: Final = -1


def get_provider_cache(provider: str, media_type: str, media_id: str,
                       season: int = _NO_PART, episode: int = _NO_PART) -> Optional[dict]:
    """Get a cached provider response; an expiry set before the title was known is re-derived."""
    key = (provider, media_type, media_id, season, episode)
    with get_db() as cursor:
        cursor.execute(
            "SELECT fetched_at, expires_at, data FROM provider_response WHERE provider = ? "
            "AND media_type = ? AND media_id = ? AND season = ? AND episode = ?", key
        )
        row = cursor.fetchone()
    if not row:
        return None

    now = int(time.time())
    if row["expires_at"] > now:
        return _decompress_data(row["data"])

    # a first fetch can beat its own title into the cache, leaving the expiry a guess
    revised = row["fetched_at"] + _provider_ttl_hours(media_id, None) * 3600
    if revised <= now:
        return None
    with get_db() as cursor:
        cursor.execute(
            "UPDATE provider_response SET expires_at = ? WHERE provider = ? AND media_type = ? "
            "AND media_id = ? AND season = ? AND episode = ?", (revised,) + key
        )
    return _decompress_data(row["data"])


def _provider_ttl_hours(media_id: str, release_date: Optional[str]) -> int:
    """TTL for a provider row, taken from the title's columns when the id resolves to one."""
    if media_id.startswith("tmdb_"):
        tmdb_id, imdb_id = media_id[5:], ""
    elif media_id.startswith("imdb_"):
        tmdb_id, imdb_id = "", media_id[5:]
    elif media_id.startswith("tt"):
        tmdb_id, imdb_id = "", media_id
    elif media_id.isdigit():
        # Trakt keys on the bare TMDB id when it has no slug or IMDb id yet
        tmdb_id, imdb_id = media_id, ""
    else:
        tmdb_id, imdb_id = "", ""

    for media_type in ("movie", "tvshow"):
        resolved = tmdb_id or (get_tmdb_id_by_imdb(imdb_id, media_type) if imdb_id else "")
        if not resolved:
            continue
        ttl = get_title_ttl_hours(media_type, resolved)
        if ttl:
            return ttl
    return get_cache_ttl_hours(release_date)


def cached_provider_keys(provider: str, media_type: str) -> Set[Tuple[str, int, int]]:
    """Every unexpired key held for a provider, for callers sizing work across a whole library."""
    with get_db() as cursor:
        cursor.execute(
            "SELECT media_id, season, episode FROM provider_response "
            "WHERE provider = ? AND media_type = ? AND expires_at > ?",
            (provider, media_type, int(time.time())))
        return {(row["media_id"], row["season"], row["episode"]) for row in cursor.fetchall()}


def save_provider_cache(provider: str, media_type: str, media_id: str, data: dict,
                        release_date: Optional[str] = None,
                        season: int = _NO_PART, episode: int = _NO_PART) -> None:
    """Save a compressed provider response under an expiry fixed at fetch time."""
    now = int(time.time())
    expires_at = now + _provider_ttl_hours(media_id, release_date) * 3600
    with get_db() as cursor:
        cursor.execute(
            "INSERT INTO provider_response "
            "(provider, media_type, media_id, season, episode, fetched_at, expires_at, data) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (provider, media_type, media_id, season, episode) DO UPDATE SET "
            "fetched_at = excluded.fetched_at, expires_at = excluded.expires_at, "
            "data = excluded.data",
            (provider, media_type, media_id, season, episode, now, expires_at,
             _compress_data(data))
        )
