"""Cache tables for provider responses, online properties and the fanart.tv feed, with TTLs."""
from __future__ import annotations

import random
import time
import xbmc
from datetime import datetime
from typing import Any, NamedTuple, Optional, Dict, List, Set, Tuple, Final

from lib.data.database._infrastructure import (
    as_int,
    get_db,
    DB_PATH,
    compress_data as _compress_data,
    decompress_data as _decompress_data,
    sql_placeholders,
    chunked_in_modify,
)
from lib.data.database.mapping import FIND_MISS_TTL_DAYS
from lib.data.database.pvr import prune_pvr_matches
from lib.kodi.client import log

# under TMDB's six-month cache limit
_TMDB_KEEP_DAYS: Final = 170


class CacheKey(NamedTuple):
    """Identity of an online-properties row; item_id is the TMDB id, or the IMDb id when unknown."""
    media_type: str
    item_id: str
    scope: str = ''


def _expiry(ttl_hours: float) -> int:
    """Absolute expiry as a Unix epoch."""
    return int(time.time() + ttl_hours * 3600)


def _now() -> int:
    """Current time as a Unix epoch."""
    return int(time.time())


def _tv_show_ttl(hints: Dict[str, Any]) -> int:
    """Hours to cache a TV show, from how near its next episode is and whether it has ended."""
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
    """Cache TTL in hours: 24 off-library, else age-tiered for movies, status-driven for TV."""

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
    """Get a cached artwork list, or None when missing or expired."""
    return _fetch_cached(
        'artwork_cache',
        'media_type = ? AND media_id = ? AND source = ? AND art_type = ? AND expires_at > ?',
        (media_type, media_id, source, art_type, _now()), 'artwork')


def get_cached_artwork_batch(
    media_type: str,
    media_ids: Dict[str, str],
    art_types: List[str]
) -> Dict[Tuple[str, str], list]:
    """Get cached artwork for several sources at once, keyed by (source, art_type)."""
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

    query_params = [media_type] + params + art_types + [_now()]

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
    """Cache an artwork list, with a TTL derived from the release date unless one is given."""
    if ttl_hours is None:
        ttl_hours = get_cache_ttl_hours(release_date)

    with get_db(DB_PATH) as cursor:
        cursor.execute(
            'INSERT INTO artwork_cache '
            '(media_type, media_id, source, art_type, expires_at, data) '
            'VALUES (?, ?, ?, ?, ?, ?) '
            'ON CONFLICT (media_type, media_id, source, art_type) DO UPDATE SET '
            'expires_at = excluded.expires_at, data = excluded.data',
            (media_type, media_id, source, art_type, _expiry(ttl_hours), _compress_data(data)),
        )


def _fetch_cached(table: str, where: str, params: tuple, label: str) -> Optional[Any]:
    """Fetch the decompressed `data` of one cache row; None when missing or unreadable."""
    with get_db(DB_PATH) as cursor:
        cursor.execute(f"SELECT data FROM {table} WHERE {where}", params)

        row = cursor.fetchone()
        if not row:
            return None

        try:
            return _decompress_data(row['data'])
        except Exception as e:
            log("Cache", f"Failed to decompress {label}: {e}", xbmc.LOGERROR)
            return None


def get_cached_metadata(media_type: str, tmdb_id: str) -> Optional[dict]:
    """Get cached TMDB title metadata, or None when missing or expired."""
    return _fetch_cached(
        'tmdb_title', 'media_type = ? AND tmdb_id = ? AND expires_at > ?',
        (media_type, tmdb_id, _now()), 'metadata')


def get_title_ttl_hours(media_type: str, tmdb_id: str) -> Optional[int]:
    """Get an item's TTL from its title row's columns, without decompressing the payload."""
    numeric_id = as_int(tmdb_id)
    if numeric_id is None:
        return None
    with get_db(DB_PATH) as cursor:
        cursor.execute(
            'SELECT status, release_date, last_air_date, next_air_date, next_complete, '
            'aired_complete FROM tmdb_title '
            # a mapping seed row has no payload to derive a TTL from
            'WHERE media_type = ? AND tmdb_id = ? AND fetched_at > 0',
            (media_type, numeric_id)
        )
        row = cursor.fetchone()
    if not row:
        return None

    hints: Dict[str, Any] = {}
    if row['status']:
        hints['status'] = row['status']
    if row['next_air_date']:
        key = 'next_episode_air_date' if row['next_complete'] \
            else 'next_episode_air_date_incomplete'
        hints[key] = row['next_air_date']
    if row['last_air_date']:
        hints['last_air_date'] = row['last_air_date']
    if row['aired_complete']:
        hints['aired_data_complete'] = 'true'
    return get_cache_ttl_hours(row['release_date'], hints)


def _title_scalars(data: dict, release_date: Optional[str]) -> tuple:
    """Promote the fields every TTL and schedule decision reads out of the payload."""
    ext = data.get('external_ids') or {}
    last_ep = data.get('last_episode_to_air') or {}
    next_ep = data.get('next_episode_to_air') or {}
    aired_complete = bool(
        data.get('overview')
        and (data.get('credits', {}) or {}).get('cast')
        and ext.get('imdb_id')
        and (data.get('content_ratings', {}) or {}).get('results')
        and last_ep.get('overview')
    )
    tvdb = ext.get('tvdb_id')
    return (
        ext.get('imdb_id') or None,
        int(tvdb) if tvdb else None,
        data.get('title') or data.get('name') or None,
        data.get('status') or None,
        release_date or data.get('release_date') or data.get('first_air_date') or None,
        last_ep.get('air_date') or None,
        next_ep.get('air_date') or None,
        1 if (next_ep.get('name') and next_ep.get('overview')) else 0,
        1 if aired_complete else 0,
        data.get('vote_average'),
        data.get('vote_count'),
    )


def cache_metadata(
    media_type: str, tmdb_id: str, data: dict, release_date: Optional[str],
    hints: Optional[Dict[str, Any]] = None, ttl_hours: Optional[int] = None,
) -> None:
    """Cache the payload with its scalars promoted to columns, under a dynamic TTL."""
    numeric_id = as_int(tmdb_id)
    if numeric_id is None:
        return
    if ttl_hours is None:
        ttl_hours = get_cache_ttl_hours(release_date, hints)
    scalars = _title_scalars(data, release_date)

    with get_db(DB_PATH) as cursor:
        cursor.execute(
            'INSERT INTO tmdb_title (media_type, tmdb_id, imdb_id, tvdb_id, title, status, '
            'release_date, last_air_date, next_air_date, next_complete, aired_complete, '
            'vote_average, vote_count, fetched_at, expires_at, data) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) '
            'ON CONFLICT (media_type, tmdb_id) DO UPDATE SET '
            # a response without external_ids must not clear the ids already stored
            'imdb_id = COALESCE(excluded.imdb_id, imdb_id), '
            'tvdb_id = COALESCE(excluded.tvdb_id, tvdb_id), title = excluded.title, '
            'status = excluded.status, release_date = excluded.release_date, '
            'last_air_date = excluded.last_air_date, next_air_date = excluded.next_air_date, '
            'next_complete = excluded.next_complete, aired_complete = excluded.aired_complete, '
            'vote_average = excluded.vote_average, vote_count = excluded.vote_count, '
            'fetched_at = excluded.fetched_at, expires_at = excluded.expires_at, '
            'data = excluded.data',
            (media_type, numeric_id) + scalars + (_now(), _expiry(ttl_hours),
                                                    _compress_data(data)))


def get_cached_season_metadata(tmdb_id: str, season_number: int) -> Optional[dict]:
    """Get a cached TMDB season-details response, or None when missing or expired."""
    return _fetch_cached(
        'tmdb_season', 'tmdb_id = ? AND season = ? AND expires_at > ?',
        (tmdb_id, season_number, _now()), 'season metadata')


def cache_season_metadata(tmdb_id: str, season_number: int, data: dict,
                          ttl_hours: Optional[int] = None) -> None:
    """Cache a TMDB season-details response, its TTL from the airing state unless given."""
    if ttl_hours is None:
        ttl_hours = _season_ttl_hours(data)
    with get_db(DB_PATH) as cursor:
        cursor.execute(
            'INSERT INTO tmdb_season (tmdb_id, season, fetched_at, expires_at, data) '
            'VALUES (?, ?, ?, ?, ?) '
            'ON CONFLICT (tmdb_id, season) DO UPDATE SET '
            'fetched_at = excluded.fetched_at, expires_at = excluded.expires_at, '
            'data = excluded.data',
            (tmdb_id, season_number, _now(), _expiry(ttl_hours), _compress_data(data)))


def _season_ttl_hours(season_data: dict) -> int:
    """Pick the season TTL: 24h while empty or any episode is unaired, else 30 days."""
    today = datetime.now().date().isoformat()
    episodes = season_data.get("episodes") or []
    if not episodes:
        return 24
    for ep in episodes:
        air = ep.get("air_date") or ""
        if not air or air > today:
            return 24
    return 24 * 30


def get_cached_tmdb_genre_list(tmdb_type: str) -> Optional[Dict[int, str]]:
    """Get the cached TMDB genre id-to-name mapping for movies or TV, or None when expired."""
    decoded = _fetch_cached(
        'blob_cache', "kind = 'tmdb_genre' AND cache_key = ? AND expires_at > ?",
        (tmdb_type, _now()), 'genre list')
    if decoded is None:
        return None

    try:
        return {int(k): v for k, v in decoded.items()}
    except (ValueError, TypeError, AttributeError) as e:
        log("Cache", f"Failed to read genre list: {e}", xbmc.LOGERROR)
        return None


def cache_tmdb_genre_list(tmdb_type: str, mapping: Dict[int, str], ttl_hours: int = 24) -> None:
    """Cache the TMDB genre id-to-name mapping for movies or TV."""
    with get_db(DB_PATH) as cursor:
        cursor.execute(
            "INSERT INTO blob_cache (kind, cache_key, expires_at, data) "
            "VALUES ('tmdb_genre', ?, ?, ?) "
            'ON CONFLICT (kind, cache_key) DO UPDATE SET '
            'expires_at = excluded.expires_at, data = excluded.data',
            (tmdb_type, _expiry(ttl_hours),
             _compress_data({str(k): v for k, v in mapping.items()})))


def get_cached_show_calendar() -> Optional[dict]:
    """Get the cached show calendar, past its refresh time or not; None when none is kept."""
    return _fetch_cached(
        'blob_cache', "kind = 'trakt_calendar' AND cache_key = 'shows' AND expires_at > ?",
        (_now(),), 'show calendar')


def cache_show_calendar(calendar: dict, keep_days: int = 3) -> None:
    """Cache the show calendar, kept for days as the fallback when a refetch fails."""
    with get_db(DB_PATH) as cursor:
        cursor.execute(
            "INSERT INTO blob_cache (kind, cache_key, expires_at, data) "
            "VALUES ('trakt_calendar', 'shows', ?, ?) "
            'ON CONFLICT (kind, cache_key) DO UPDATE SET '
            'expires_at = excluded.expires_at, data = excluded.data',
            (_expiry(keep_days * 24), _compress_data(calendar)))


def get_cached_trakt(cache_key: str) -> Optional[Any]:
    """Get a cached Trakt response, or None when missing or expired."""
    return _fetch_cached(
        'blob_cache', "kind = 'trakt' AND cache_key = ? AND expires_at > ?",
        (cache_key, _now()), 'Trakt data')


def cache_trakt(cache_key: str, data: Any, ttl_hours: float) -> None:
    """Cache a Trakt response under a caller-set TTL."""
    with get_db(DB_PATH) as cursor:
        cursor.execute(
            "INSERT INTO blob_cache (kind, cache_key, expires_at, data) "
            "VALUES ('trakt', ?, ?, ?) "
            'ON CONFLICT (kind, cache_key) DO UPDATE SET '
            'expires_at = excluded.expires_at, data = excluded.data',
            (cache_key, _expiry(ttl_hours), _compress_data(data)))


def get_fresh_title_ids(media_type: str) -> Set[str]:
    """Get the TMDB ids of one media type whose cached title data is still fresh."""
    with get_db(DB_PATH) as cursor:
        cursor.execute(
            'SELECT tmdb_id FROM tmdb_title WHERE media_type = ? AND expires_at > ?',
            (media_type, _now()))
        return {str(row['tmdb_id']) for row in cursor.fetchall()}


def expire_metadata(media_type: str, tmdb_id: str, ttl_hours: int = 12) -> None:
    """Shorten a title's cache TTL so the next read refetches; an earlier expiry is kept."""
    with get_db(DB_PATH) as cursor:
        cursor.execute(
            'UPDATE tmdb_title SET expires_at = MIN(expires_at, ?) '
            'WHERE media_type = ? AND tmdb_id = ?',
            (_expiry(ttl_hours), media_type, tmdb_id))


def clear_expired_cache() -> int:
    """Clear expired cache rows; the rows callers still read through are kept."""
    now = _now()
    with get_db(DB_PATH) as cursor:
        cursor.execute('DELETE FROM artwork_cache WHERE expires_at < ?', (now,))
        artwork_deleted = cursor.rowcount

        # the row also carries the id mapping, which outlives the payload
        cursor.execute(
            "UPDATE tmdb_title SET data = X'' WHERE fetched_at < ? AND LENGTH(data) > 0",
            (now - _TMDB_KEEP_DAYS * 86400,))
        metadata_trimmed = cursor.rowcount

        cursor.execute('DELETE FROM tmdb_season WHERE expires_at < ?', (now,))
        season_deleted = cursor.rowcount

        cursor.execute('DELETE FROM blob_cache WHERE expires_at < ?', (now,))
        genre_deleted = cursor.rowcount

        cursor.execute('DELETE FROM tmdb_person WHERE expires_at < ?', (now,))
        person_deleted = cursor.rowcount

        # stale online props are still served until a refresh replaces them
        cursor.execute('DELETE FROM online_props WHERE fetched_at < ?',
                       (now - _TMDB_KEEP_DAYS * 86400,))
        online_deleted = cursor.rowcount

        cursor.execute('DELETE FROM provider_response WHERE expires_at < ?', (now,))
        provider_deleted = cursor.rowcount

        cursor.execute('DELETE FROM tmdb_episode_miss WHERE expires_at < ?', (now,))
        episode_miss_deleted = cursor.rowcount

        cursor.execute('DELETE FROM tmdb_find_miss WHERE checked_at < ?',
                       (now - FIND_MISS_TTL_DAYS * 86400,))
        find_miss_deleted = cursor.rowcount

        deleted = (artwork_deleted + metadata_trimmed + season_deleted + genre_deleted
                   + person_deleted + online_deleted + provider_deleted
                   + episode_miss_deleted + find_miss_deleted)

    deleted += prune_pvr_matches()
    if deleted > 0:
        log("Database", f"Cleared {deleted} expired cache entries")

    return deleted


def cache_person_data(person_id: int, data: dict, ttl_days: int = 30) -> None:
    """Cache compressed TMDB person data with a days-based TTL."""
    with get_db(DB_PATH) as cursor:
        cursor.execute('''
            INSERT INTO tmdb_person (person_id, expires_at, data) VALUES (?, ?, ?)
            ON CONFLICT (person_id) DO UPDATE SET
                expires_at = excluded.expires_at, data = excluded.data
        ''', (person_id, _expiry(ttl_days * 24), _compress_data(data)))


def get_cached_person_data(person_id: int) -> Optional[dict]:
    """Get cached TMDB person data, or None when missing or expired."""
    return _fetch_cached(
        'tmdb_person', 'person_id = ? AND expires_at > ?',
        (person_id, _now()), 'person data')


def get_cached_online_properties(key: CacheKey) -> Optional[Dict[str, str]]:
    """Get cached online properties, stale ones included until a refresh overwrites them."""
    return _fetch_cached(
        'online_props', 'media_type = ? AND item_id = ? AND scope = ?',
        tuple(key), 'online properties')


def get_cached_online_properties_state(
    key: CacheKey,
) -> Tuple[Optional[Dict[str, str]], int]:
    """Get cached online properties with the row's expiry epoch; (None, 0) with no readable row."""
    with get_db(DB_PATH) as cursor:
        cursor.execute(
            'SELECT data, expires_at FROM online_props '
            'WHERE media_type = ? AND item_id = ? AND scope = ?',
            tuple(key)
        )
        row = cursor.fetchone()
        if not row:
            return None, 0

        try:
            props = _decompress_data(row['data'])
        except Exception as e:
            log("Cache", f"Failed to decompress online properties: {e}", xbmc.LOGERROR)
            return None, 0

        return props, row['expires_at']


def get_mb_id_aliases(canonical_id: str) -> List[str]:
    """Get all known old IDs that redirect to this canonical ID."""
    with get_db(DB_PATH) as cursor:
        cursor.execute('SELECT old_id FROM mb_id_alias WHERE canonical_id = ?', (canonical_id,))
        return [row['old_id'] for row in cursor.fetchall()]


def save_mb_id_mapping(old_id: str, canonical_id: str) -> None:
    """Save an old-to-canonical MusicBrainz ID mapping, which never expires."""
    with get_db(DB_PATH) as cursor:
        cursor.execute(
            'INSERT INTO mb_id_alias (old_id, canonical_id, cached_at) VALUES (?, ?, ?) '
            'ON CONFLICT (old_id) DO UPDATE SET canonical_id = excluded.canonical_id',
            (old_id, canonical_id, _now())
        )


_online_generation = 0


def online_cache_generation() -> int:
    """Bumped on every online-properties invalidation, so callers can drop a memo."""
    return _online_generation


def invalidate_online_properties(media_type: str, imdb_id: str = '', tmdb_id: str = '') -> int:
    """Invalidate an item's cached online properties in every scope, bumping the generation."""
    global _online_generation
    _online_generation += 1
    item_ids = [i for i in (tmdb_id, imdb_id) if i]
    if not item_ids:
        return 0
    total = 0
    with get_db(DB_PATH) as cursor:
        for item_id in item_ids:
            cursor.execute(
                'DELETE FROM online_props WHERE media_type = ? AND item_id = ?',
                (media_type, item_id))
            total += cursor.rowcount
    if total > 0:
        log("Cache", "Invalidated {} online cache entries for {}".format(total, media_type))
    return total


def expire_online_properties_by_keys(keys: List[CacheKey]) -> int:
    """Expire cached online properties by exact key, bumping the generation; the data stays."""
    global _online_generation
    _online_generation += 1
    if not keys:
        return 0
    total = 0
    with get_db(DB_PATH) as cursor:
        for key in keys:
            cursor.execute(
                'UPDATE online_props SET expires_at = 0 '
                'WHERE media_type = ? AND item_id = ? AND scope = ?', tuple(key))
            total += cursor.rowcount
    if total > 0:
        log("Cache", f"Expired {total} stale online cache entries")
    return total


def cache_online_properties(key: CacheKey, props: Dict[str, str], ttl_hours: int = 1) -> None:
    """Store the property dict a fetch produced for one item."""
    now = _now()
    with get_db(DB_PATH) as cursor:
        cursor.execute('''
            INSERT INTO online_props
                (media_type, item_id, scope, fetched_at, expires_at, data)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (media_type, item_id, scope) DO UPDATE SET
                fetched_at = excluded.fetched_at,
                expires_at = excluded.expires_at,
                data = excluded.data
        ''', (key.media_type, key.item_id, key.scope, now,
              _expiry(ttl_hours), _compress_data(props)))


def merge_online_properties(key: CacheKey, props: Dict[str, str]) -> None:
    """Merge properties into an item's cached row, keeping its expiry; a new row starts expired."""
    with get_db(DB_PATH) as cursor:
        cursor.execute(
            'SELECT data FROM online_props '
            'WHERE media_type = ? AND item_id = ? AND scope = ?', tuple(key))
        row = cursor.fetchone()
        merged: Dict[str, str] = {}
        if row:
            try:
                merged = _decompress_data(row['data'])
            except Exception as e:
                log("Cache", f"Failed to decompress online properties: {e}", xbmc.LOGERROR)
        merged.update(props)
        cursor.execute('''
            INSERT INTO online_props
                (media_type, item_id, scope, fetched_at, expires_at, data)
            VALUES (?, ?, ?, ?, 0, ?)
            ON CONFLICT (media_type, item_id, scope) DO UPDATE SET
                fetched_at = excluded.fetched_at,
                data = excluded.data
        ''', (key.media_type, key.item_id, key.scope, _now(), _compress_data(merged)))


def get_feed_checkpoint(feed: str) -> int:
    """Get the Unix time the fanart.tv feed was last read, or 0 if never."""
    with get_db(DB_PATH) as cursor:
        cursor.execute('SELECT checked_at FROM fanarttv_feed WHERE feed = ?', (feed,))
        row = cursor.fetchone()
        return int(row['checked_at']) if row else 0


def set_feed_checkpoint(feed: str, checked_at: int) -> None:
    """Set how far through the fanart.tv feed we have read."""
    with get_db(DB_PATH) as cursor:
        cursor.execute(
            'INSERT OR REPLACE INTO fanarttv_feed (feed, checked_at) VALUES (?, ?)',
            (feed, int(checked_at))
        )


def add_rechecks(feed: str, item_ids: List[str], recheck_after: int) -> None:
    """Add rechecks for items the feed reported changed, due once the key delay has passed."""
    if not item_ids:
        return
    with get_db(DB_PATH) as cursor:
        cursor.executemany(
            'INSERT OR REPLACE INTO fanarttv_recheck (feed, item_id, recheck_after) '
            'VALUES (?, ?, ?)',
            [(feed, item_id, int(recheck_after)) for item_id in item_ids]
        )


def take_due_rechecks(feed: str, now: Optional[int] = None) -> List[str]:
    """Take the item ids whose recheck is due, removing them so each is handled once."""
    stamp = _now() if now is None else int(now)
    with get_db(DB_PATH) as cursor:
        cursor.execute(
            'SELECT item_id FROM fanarttv_recheck WHERE feed = ? AND recheck_after <= ?',
            (feed, stamp)
        )
        due = [row['item_id'] for row in cursor.fetchall()]
        chunked_in_modify(
            cursor, 'DELETE FROM fanarttv_recheck WHERE feed = ? AND item_id IN ({placeholders})',
            [feed], due)
        return due


def clear_artwork_for_ids(media_ids: List[str]) -> int:
    """Clear cached artwork, completion marker included, for the given provider ids."""
    if not media_ids:
        return 0
    with get_db(DB_PATH) as cursor:
        return chunked_in_modify(
            cursor, 'DELETE FROM artwork_cache WHERE media_id IN ({placeholders})', [], media_ids)
