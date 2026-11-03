"""Cross-provider ID resolution over `tmdb_title`, plus the negative `/find` cache."""
from __future__ import annotations

import time
from typing import Dict, List, Optional, Final

from lib.data.database._infrastructure import as_int, get_db, chunked_in_query

FIND_MISS_TTL_DAYS: Final = 30


def save_id_mapping(
    tmdb_id: str,
    media_type: str,
    imdb_id: Optional[str] = None,
    tvdb_id: Optional[str] = None,
) -> None:
    """Save an id pairing, seeding a payload-less row when the title is not cached yet."""
    numeric_id = as_int(tmdb_id)
    if numeric_id is None or not media_type:
        return
    with get_db() as cursor:
        cursor.execute(
            "INSERT INTO tmdb_title (media_type, tmdb_id, imdb_id, tvdb_id, "
            "fetched_at, expires_at, data) VALUES (?, ?, ?, ?, 0, 0, X'') "
            "ON CONFLICT (media_type, tmdb_id) DO UPDATE SET "
            "imdb_id = COALESCE(excluded.imdb_id, imdb_id), "
            "tvdb_id = COALESCE(excluded.tvdb_id, tvdb_id)",
            (media_type, numeric_id, imdb_id or None, as_int(tvdb_id)),
        )


def _lookup(select_col: str, where_col: str, value, media_type: str) -> Optional[str]:
    """Single-column id lookup, unfiltered by expiry since ids outlive the payload."""
    if value is None or value == '':
        return None
    with get_db() as cursor:
        cursor.execute(
            f"SELECT {select_col} FROM tmdb_title WHERE {where_col} = ? AND media_type = ?",
            (value, media_type),
        )
        row = cursor.fetchone()
        return str(row[select_col]) if row and row[select_col] else None


def get_imdb_id(tmdb_id: str, media_type: str) -> Optional[str]:
    """Get the IMDb id mapped to a TMDB id, or None."""
    return _lookup("imdb_id", "tmdb_id", as_int(tmdb_id), media_type)


def get_imdb_ids_batch(tmdb_ids: set, media_type: str) -> Dict[str, str]:
    """Get the IMDb ids mapped to many TMDB ids; an unmapped id is left out."""
    if not tmdb_ids:
        return {}
    wanted = [i for i in (as_int(t) for t in tmdb_ids) if i is not None]
    if not wanted:
        return {}
    results: Dict[str, str] = {}
    sql = (
        "SELECT tmdb_id, imdb_id FROM tmdb_title "
        "WHERE media_type = ? AND tmdb_id IN ({placeholders})"
    )
    with get_db() as cursor:
        for row in chunked_in_query(cursor, sql, [media_type], wanted):
            if row["imdb_id"]:
                results[str(row["tmdb_id"])] = row["imdb_id"]
    return results


def get_tmdb_id_by_imdb(imdb_id: str, media_type: str) -> Optional[str]:
    """Get the TMDB id mapped to an IMDb id, or None."""
    return _lookup("tmdb_id", "imdb_id", imdb_id, media_type)


def get_tmdb_id_by_tvdb(tvdb_id: str, media_type: str) -> Optional[str]:
    """Get the TMDB id mapped to a TVDB id, or None."""
    return _lookup("tmdb_id", "tvdb_id", as_int(tvdb_id), media_type)


def get_tmdb_ids_by_tvdb(tvdb_ids: List[str], media_type: str) -> List[str]:
    """Get the TMDB ids mapped to many TVDB ids; an unmapped id is left out."""
    wanted = [i for i in (as_int(t) for t in tvdb_ids) if i is not None]
    if not wanted:
        return []
    sql = "SELECT tmdb_id FROM tmdb_title WHERE media_type = ? AND tvdb_id IN ({placeholders})"
    with get_db() as cursor:
        return [str(row["tmdb_id"]) for row in chunked_in_query(cursor, sql, [media_type], wanted)]


def is_known_find_miss(imdb_id: str, media_type: str) -> bool:
    """True while a recent TMDB `/find` for this id is known to have returned nothing."""
    with get_db() as cursor:
        cursor.execute(
            "SELECT 1 FROM tmdb_find_miss WHERE imdb_id = ? AND media_type = ? "
            "AND checked_at > ?",
            (imdb_id, media_type, int(time.time()) - FIND_MISS_TTL_DAYS * 86400),
        )
        return cursor.fetchone() is not None


def save_find_miss(imdb_id: str, media_type: str) -> None:
    """Save that TMDB has no title for this IMDb id."""
    with get_db() as cursor:
        cursor.execute(
            "INSERT INTO tmdb_find_miss (imdb_id, media_type, checked_at) VALUES (?, ?, ?) "
            "ON CONFLICT (imdb_id, media_type) DO UPDATE SET checked_at = excluded.checked_at",
            (imdb_id, media_type, int(time.time())),
        )


def is_known_episode_miss(tmdb_id: str, season: int, episode: int) -> bool:
    """True while TMDB is known to hold this episode with no IMDb id."""
    numeric_id = as_int(tmdb_id)
    if numeric_id is None:
        return False
    with get_db() as cursor:
        cursor.execute(
            "SELECT 1 FROM tmdb_episode_miss "
            "WHERE tmdb_id = ? AND season = ? AND episode = ? AND expires_at > ?",
            (numeric_id, season, episode, int(time.time())),
        )
        return cursor.fetchone() is not None


def save_episode_miss(tmdb_id: str, season: int, episode: int,
                      air_date: Optional[str] = None) -> None:
    """Save that TMDB holds this episode with no IMDb id, aged off its own air date."""
    numeric_id = as_int(tmdb_id)
    if numeric_id is None:
        return
    from lib.data.database.cache import get_cache_ttl_hours
    _store_episode_miss(numeric_id, season, episode, get_cache_ttl_hours(air_date))


def save_unlisted_episode(tmdb_id: str, season: int, episode: int) -> None:
    """Record an episode TMDB does not list at all, for the same window as a `/find` miss."""
    numeric_id = as_int(tmdb_id)
    if numeric_id is not None:
        _store_episode_miss(numeric_id, season, episode, FIND_MISS_TTL_DAYS * 24)


def _store_episode_miss(tmdb_id: int, season: int, episode: int, ttl_hours: int) -> None:
    """Upsert an episode miss that expires after the given hours."""
    expires = int(time.time()) + ttl_hours * 3600
    with get_db() as cursor:
        cursor.execute(
            "INSERT INTO tmdb_episode_miss (tmdb_id, season, episode, expires_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT (tmdb_id, season, episode) DO UPDATE SET "
            "expires_at = excluded.expires_at",
            (tmdb_id, season, episode, expires),
        )
