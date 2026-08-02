"""API response caching for TMDB and fanart.tv.

Manages cache tables with dynamic TTL based on media age.
"""
from __future__ import annotations

import random
import time
import xbmc
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List, Tuple

from lib.data.database._infrastructure import (
    get_db,
    DB_PATH,
    compress_data as _compress_data,
    decompress_data as _decompress_data,
    sql_placeholders,
)
from lib.kodi.client import log


def _tv_show_ttl(hints: Dict[str, Any]) -> int:
    """Calculate TTL for TV shows based on schedule and status hints.

    Airing, complete (next ep has name + overview + air_date):
        < 7 days out:   random 24-48h
        7-30 days out:  random 3-6 days
        30+ days out:   random 14-30 days

    Airing, incomplete (next ep missing name/overview):
        < 7 days out:   24h
        7-30 days out:  random 2-4 days
        30-90 days out: random 3-6 days
        > 90 days out:  random 7-14 days

    Air date passed:        12h
    Active, no schedule:    random 3-7 days

    Ended, complete (aired_data_complete):
        Any age:        random 14-30 days

    Ended, incomplete:
        < 14 days:      random 24-72h
        14-30 days:     random 3-6 days
        30+ days:       random 7-14 days
    """
    aired_data_complete = hints.get("aired_data_complete") == "true"
    status = hints.get("status", "").lower() if hints.get("status") else ""
    next_air = hints.get("next_episode_air_date")
    next_air_incomplete = hints.get("next_episode_air_date_incomplete")
    last_air = hints.get("last_air_date")

    air_date_str = next_air or next_air_incomplete
    if air_date_str:
        try:
            days_until = (
                datetime.fromisoformat(air_date_str) - datetime.now()
            ).total_seconds() / 86400
        except (ValueError, AttributeError):
            days_until = None

        if days_until is not None:
            if days_until <= 0:
                return 12
            if next_air:
                if days_until <= 7:
                    return random.randint(24, 48)
                if days_until <= 30:
                    return random.randint(3, 6) * 24
                return random.randint(14, 30) * 24
            if days_until <= 7:
                return 24
            if days_until <= 30:
                return random.randint(2, 4) * 24
            if days_until <= 90:
                return random.randint(3, 6) * 24
            return random.randint(7, 14) * 24

    if status in ("ended", "canceled"):
        if aired_data_complete:
            return random.randint(14, 30) * 24

        days_since_last = None
        if last_air:
            try:
                days_since_last = (datetime.now() - datetime.fromisoformat(last_air)).days
            except (ValueError, AttributeError):
                pass

        if days_since_last is not None and days_since_last < 14:
            return random.randint(24, 72)
        if days_since_last is not None and days_since_last < 30:
            return random.randint(3, 6) * 24
        return random.randint(7, 14) * 24

    return random.randint(3, 7) * 24


def get_cache_ttl_hours(
    release_date: Optional[str], hints: Optional[Dict[str, Any]] = None
) -> int:
    """Dynamic cache TTL (hours) based on content status and metadata hints.

    Movies age-tiered off `release_date`:
      <90d random 24-48h, <1y random 3-6d, <2y random 7-14d, >2y random 14-30d,
      unknown random 24-48h.
    TV shows ignore `release_date` and route through `_tv_show_ttl(hints)`.

    Recognised `hints` keys: status, next_episode_air_date,
    next_episode_air_date_incomplete, last_air_date, aired_data_complete,
    is_library_item (False forces 24h).
    """

    hints = hints or {}

    if hints.get("is_library_item") is False:
        return 24

    status = hints.get("status", "").lower() if hints.get("status") else ""
    has_tv_hints = (
        hints.get("next_episode_air_date")
        or hints.get("next_episode_air_date_incomplete")
        or status in ("ended", "canceled", "returning series", "in production", "planned", "pilot")
    )

    if has_tv_hints:
        return _tv_show_ttl(hints)

    if release_date:
        try:
            release = datetime.fromisoformat(release_date)
            days_old = (datetime.now() - release).days
            if days_old < 90:
                return random.randint(24, 48)
            if days_old < 365:
                return random.randint(3, 6) * 24
            if days_old < 730:
                return random.randint(7, 14) * 24
            return random.randint(14, 30) * 24
        except (ValueError, AttributeError):
            return random.randint(24, 48)
    return random.randint(24, 48)


def get_fanarttv_cache_ttl_hours() -> int:
    """Cache TTL for Fanart.tv: 48h with personal key, 168h on project key."""
    from lib.kodi.settings import KodiSettings
    if KodiSettings.fanarttv_api_key():
        return 48
    return 168


def get_cached_artwork(
    media_type: str, media_id: str, source: str, art_type: str
) -> Optional[list]:
    """Return cached artwork list, or None if missing/expired."""
    with get_db(DB_PATH) as cursor:
        cursor.execute('''
            SELECT data FROM artwork_cache
            WHERE media_type = ? AND media_id = ? AND source = ? AND art_type = ?
              AND expires_at > ?
        ''', (media_type, media_id, source, art_type, datetime.now().isoformat()))

        row = cursor.fetchone()

        if not row:
            return None

        try:
            return _decompress_data(row['data'])
        except Exception as e:
            log("Cache", f"Failed to parse cached data: {str(e)}", xbmc.LOGERROR)
            return None


def get_cached_artwork_batch(
    media_type: str,
    media_ids: Dict[str, str],
    art_types: List[str]
) -> Dict[Tuple[str, str], list]:
    """Batch artwork lookup. `media_ids` is source -> id; returns (source, art_type) -> list."""
    if not media_ids or not art_types:
        return {}

    conditions = []
    params = []

    for source, media_id in media_ids.items():
        if media_id:
            conditions.append("(source = ? AND media_id = ?)")
            params.append(source)
            params.append(media_id)

    if not conditions:
        return {}

    art_type_placeholders = sql_placeholders(len(art_types))

    query = f'''
        SELECT source, art_type, data
        FROM artwork_cache
        WHERE media_type = ?
          AND ({' OR '.join(conditions)})
          AND art_type IN ({art_type_placeholders})
          AND expires_at > ?
    '''

    query_params = [media_type] + params + art_types + [datetime.now().isoformat()]

    with get_db(DB_PATH) as cursor:
        cursor.execute(query, query_params)
        rows = cursor.fetchall()

        results: Dict[Tuple[str, str], list] = {}

        for row in rows:
            try:
                key = (row['source'], row['art_type'])
                results[key] = _decompress_data(row['data'])
            except Exception as e:
                log("Cache", f"Failed to parse cached data: {str(e)}", xbmc.LOGERROR)
                continue

        return results


def cache_artwork(
    media_type: str, media_id: str, source: str, art_type: str, data: list,
    release_date: Optional[str] = None, ttl_hours: Optional[int] = None,
) -> None:
    """Cache artwork list. TTL derived from `release_date` unless `ttl_hours` is given."""
    if ttl_hours is None:
        ttl_hours = get_cache_ttl_hours(release_date)

    with get_db(DB_PATH) as cursor:
        expires_at = datetime.now() + timedelta(hours=ttl_hours)

        cursor.execute(
            '\n'
            '            INSERT OR REPLACE INTO artwork_cache '
            '(media_type, media_id, source, art_type, data, release_date, expires_at)\n'
            '            VALUES (?, ?, ?, ?, ?, ?, ?)\n'
            '        ',
            (
                media_type, media_id, source, art_type, _compress_data(data),
                release_date, expires_at.isoformat(),
            ),
        )


def get_cached_metadata(media_type: str, tmdb_id: str) -> Optional[dict]:
    """Return cached extended metadata, or None if missing/expired."""
    with get_db(DB_PATH) as cursor:
        cursor.execute('''
            SELECT data FROM metadata_cache
            WHERE media_type = ? AND tmdb_id = ?
              AND expires_at > ?
        ''', (media_type, tmdb_id, datetime.now().isoformat()))

        row = cursor.fetchone()
        if not row:
            return None

        try:
            return _decompress_data(row['data'])
        except Exception as e:
            log("Cache", f"Failed to decompress metadata: {e}", xbmc.LOGERROR)
            return None


def cache_metadata(
    media_type: str, tmdb_id: str, data: dict, release_date: Optional[str],
    hints: Optional[Dict[str, Any]] = None, ttl_hours: Optional[int] = None,
) -> None:
    """Cache zlib-compressed metadata with dynamic TTL.

    For movies/tvshows, also copies `external_ids` into the id_mappings table.
    """
    if ttl_hours is None:
        ttl_hours = get_cache_ttl_hours(release_date, hints)
    expires_at = datetime.now() + timedelta(hours=ttl_hours)
    compressed = _compress_data(data)

    with get_db(DB_PATH) as cursor:
        cursor.execute('''
            INSERT OR REPLACE INTO metadata_cache
            (media_type, tmdb_id, data, release_date, expires_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (media_type, tmdb_id, compressed, release_date, expires_at.isoformat()))

    if media_type in ('movie', 'tvshow') and isinstance(data.get('external_ids'), dict):
        from lib.data.database.mapping import save_id_mapping
        ext = data['external_ids']
        save_id_mapping(
            tmdb_id, media_type,
            imdb_id=ext.get('imdb_id') or None,
            tvdb_id=str(ext['tvdb_id']) if ext.get('tvdb_id') else None,
        )


def get_cached_season_metadata(tmdb_id: str, season_number: int) -> Optional[dict]:
    """Return cached TMDB season-details response, or None if missing/expired."""
    with get_db(DB_PATH) as cursor:
        cursor.execute('''
            SELECT data FROM season_metadata_cache
            WHERE tmdb_id = ? AND season_number = ?
              AND expires_at > ?
        ''', (tmdb_id, season_number, datetime.now().isoformat()))

        row = cursor.fetchone()
        if not row:
            return None

        try:
            return _decompress_data(row['data'])
        except Exception as e:
            log("Cache", f"Failed to decompress season metadata: {e}", xbmc.LOGERROR)
            return None


def cache_season_metadata(tmdb_id: str, season_number: int, data: dict,
                          ttl_hours: Optional[int] = None) -> None:
    """Cache zlib-compressed TMDB season-details response.

    Default TTL: 24h if any episode hasn't aired yet (active season),
    otherwise 30 days (frozen season data).
    """
    if ttl_hours is None:
        ttl_hours = _season_ttl_hours(data)
    expires_at = datetime.now() + timedelta(hours=ttl_hours)
    compressed = _compress_data(data)

    with get_db(DB_PATH) as cursor:
        cursor.execute('''
            INSERT OR REPLACE INTO season_metadata_cache
            (tmdb_id, season_number, data, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (tmdb_id, season_number, compressed, expires_at.isoformat()))


def _season_ttl_hours(season_data: dict) -> int:
    """Pick season-cache TTL: 24h if season is still airing, 30d if all episodes have aired."""
    today = datetime.now().date().isoformat()
    episodes = season_data.get("episodes") or []
    if not episodes:
        return 6
    for ep in episodes:
        air = ep.get("air_date") or ""
        if not air or air > today:
            return 24
    return 24 * 30


def get_cached_tmdb_genre_list(tmdb_type: str) -> Optional[Dict[int, str]]:
    """Return cached TMDB genre id->name mapping for `movie` or `tv`, or None if missing/expired."""
    with get_db(DB_PATH) as cursor:
        cursor.execute('''
            SELECT data FROM tmdb_genre_cache
            WHERE tmdb_type = ? AND expires_at > ?
        ''', (tmdb_type, datetime.now().isoformat()))

        row = cursor.fetchone()
        if not row:
            return None

        try:
            decoded = _decompress_data(row['data'])
            return {int(k): v for k, v in decoded.items()}
        except Exception as e:
            log("Cache", f"Failed to decompress genre list: {e}", xbmc.LOGERROR)
            return None


def cache_tmdb_genre_list(tmdb_type: str, mapping: Dict[int, str], ttl_hours: int = 24) -> None:
    """Cache the TMDB genre id->name mapping for `movie` or `tv` (default 24h TTL)."""
    expires_at = datetime.now() + timedelta(hours=ttl_hours)
    compressed = _compress_data({str(k): v for k, v in mapping.items()})

    with get_db(DB_PATH) as cursor:
        cursor.execute('''
            INSERT OR REPLACE INTO tmdb_genre_cache
            (tmdb_type, data, expires_at)
            VALUES (?, ?, ?)
        ''', (tmdb_type, compressed, expires_at.isoformat()))


def expire_metadata(media_type: str, tmdb_id: str, ttl_hours: int = 12) -> None:
    """Shorten metadata cache TTL so the next fetch gets fresh data.

    Only shortens. If the entry already expires sooner, it's left alone.
    """
    new_expires = (datetime.now() + timedelta(hours=ttl_hours)).isoformat()
    with get_db(DB_PATH) as cursor:
        cursor.execute('''
            UPDATE metadata_cache
            SET expires_at = MIN(expires_at, ?)
            WHERE media_type = ? AND tmdb_id = ?
        ''', (new_expires, media_type, tmdb_id))


def clear_expired_cache() -> int:
    """Remove expired artwork/metadata entries and 180d+ online props; returns count removed."""
    now = datetime.now()
    with get_db(DB_PATH) as cursor:
        cursor.execute(
            'DELETE FROM artwork_cache WHERE expires_at < ?',
            (now.isoformat(),)
        )
        artwork_deleted = cursor.rowcount

        cursor.execute(
            'DELETE FROM metadata_cache WHERE expires_at < ?',
            (now.isoformat(),)
        )
        metadata_deleted = cursor.rowcount

        cursor.execute(
            'DELETE FROM season_metadata_cache WHERE expires_at < ?',
            (now.isoformat(),)
        )
        season_deleted = cursor.rowcount

        cursor.execute(
            'DELETE FROM tmdb_genre_cache WHERE expires_at < ?',
            (now.isoformat(),)
        )
        genre_deleted = cursor.rowcount

        # Stale online props served until refreshed, but purge very old entries
        cutoff = (now - timedelta(days=180)).isoformat()
        cursor.execute(
            'DELETE FROM online_properties_cache WHERE expires_at < ?',
            (cutoff,)
        )
        online_deleted = cursor.rowcount

        # provider_cache has per-read TTL logic but no expires_at column;
        # 30 days is past every computed TTL
        provider_cutoff = (now - timedelta(days=30)).isoformat()
        cursor.execute(
            'DELETE FROM provider_cache WHERE cached_at < ?',
            (provider_cutoff,)
        )
        provider_deleted = cursor.rowcount

        deleted = (artwork_deleted + metadata_deleted + season_deleted
                   + genre_deleted + online_deleted + provider_deleted)

    if deleted > 0:
        log("Database", f"Cleared {deleted} expired cache entries")

    return deleted


def cache_person_data(person_id: int, data: dict, ttl_days: int = 30) -> None:
    """Cache compressed TMDB person data with a days-based TTL."""
    now = int(time.time())
    expires = now + (ttl_days * 86400)

    with get_db(DB_PATH) as cursor:
        cursor.execute('''
            INSERT OR REPLACE INTO person_cache (person_id, data, cached_at, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (person_id, _compress_data(data), now, expires))


def get_cached_person_data(person_id: int) -> Optional[dict]:
    """Return cached TMDB person data, or None if missing/expired."""
    with get_db(DB_PATH) as cursor:
        cursor.execute('''
            SELECT data FROM person_cache
            WHERE person_id = ? AND expires_at > ?
        ''', (person_id, int(time.time())))

        row = cursor.fetchone()

        if not row:
            return None

        try:
            return _decompress_data(row['data'])
        except Exception as e:
            log("Cache", f"Failed to parse cached person data: {str(e)}", xbmc.LOGERROR)
            return None


def get_cached_online_keys() -> set:
    """Get all non-expired item_keys from online_properties_cache."""
    with get_db(DB_PATH) as cursor:
        now = datetime.now().isoformat()
        cursor.execute(
            'SELECT item_key FROM online_properties_cache WHERE expires_at > ?',
            (now,)
        )
        return {row['item_key'] for row in cursor.fetchall()}


def get_cached_online_properties(item_key: str) -> Optional[Dict[str, str]]:
    """Return cached online properties. Serves stale data until a refresh overwrites it."""
    with get_db(DB_PATH) as cursor:
        cursor.execute('''
            SELECT data FROM online_properties_cache
            WHERE item_key = ?
        ''', (item_key,))

        row = cursor.fetchone()
        if not row:
            return None

        try:
            return _decompress_data(row['data'])
        except Exception as e:
            log("Cache", f"Failed to decompress online properties: {e}", xbmc.LOGERROR)
            return None


def get_mb_id_mapping(old_id: str) -> Optional[str]:
    """Get canonical ID for an old/merged MusicBrainz release group ID."""
    with get_db(DB_PATH) as cursor:
        cursor.execute('SELECT canonical_id FROM mb_id_mappings WHERE old_id = ?', (old_id,))
        row = cursor.fetchone()
        return row['canonical_id'] if row else None


def get_mb_id_mappings_by_canonical(canonical_id: str) -> List[str]:
    """Get all known old IDs that redirect to this canonical ID."""
    with get_db(DB_PATH) as cursor:
        cursor.execute('SELECT old_id FROM mb_id_mappings WHERE canonical_id = ?', (canonical_id,))
        return [row['old_id'] for row in cursor.fetchall()]


def save_mb_id_mapping(old_id: str, canonical_id: str) -> None:
    """Store an old->canonical MusicBrainz ID mapping. Permanent because merges never reverse."""
    with get_db(DB_PATH) as cursor:
        cursor.execute(
            'INSERT OR REPLACE INTO mb_id_mappings (old_id, canonical_id) VALUES (?, ?)',
            (old_id, canonical_id)
        )


def invalidate_online_properties(media_type: str, imdb_id: str = '', tmdb_id: str = '') -> int:
    """Delete cached online properties for a specific item."""
    keys = []
    if tmdb_id:
        keys.append("{}:tmdb:{}".format(media_type, tmdb_id))
    if imdb_id:
        keys.append("{}:imdb:{}".format(media_type, imdb_id))
    if not keys:
        return 0
    total = 0
    with get_db(DB_PATH) as cursor:
        for key in keys:
            cursor.execute('DELETE FROM online_properties_cache WHERE item_key = ?', (key,))
            total += cursor.rowcount
    if total > 0:
        log("Cache", "Invalidated {} online cache entries for {}".format(total, media_type))
    return total


def invalidate_online_properties_by_keys(keys: List[str]) -> int:
    """Delete cached online properties by exact cache keys."""
    if not keys:
        return 0
    total = 0
    with get_db(DB_PATH) as cursor:
        for key in keys:
            cursor.execute('DELETE FROM online_properties_cache WHERE item_key = ?', (key,))
            total += cursor.rowcount
    if total > 0:
        log("Cache", f"Invalidated {total} stale online cache entries")
    return total


def cache_online_properties(item_key: str, props: Dict[str, str], ttl_hours: int = 1) -> None:
    """Cache a key -> value properties dict for an item (e.g. "movie:123:tt1234567:456")."""
    expires_at = datetime.now() + timedelta(hours=ttl_hours)
    compressed = _compress_data(props)

    with get_db(DB_PATH) as cursor:
        cursor.execute('''
            INSERT OR REPLACE INTO online_properties_cache
            (item_key, data, expires_at)
            VALUES (?, ?, ?)
        ''', (item_key, compressed, expires_at.isoformat()))
