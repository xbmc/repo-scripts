"""Music metadata cache database.

Separate database (music_metadata.db) for caching raw API responses from
TheAudioDB, Last.fm, and Wikipedia. Stores zlib-compressed JSON blobs; field
extraction happens at read time in the service layer.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Optional

import xbmc
import xbmcvfs

from lib.data.database._infrastructure import (
    get_db,
    compress_data as _compress,
    decompress_data as _decompress,
)
from lib.kodi.client import log

MUSIC_DB_PATH = xbmcvfs.translatePath(
    'special://profile/addon_data/script.skin.info.service/music_metadata.db'
)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS music_artists (
    source TEXT NOT NULL,
    lookup_key TEXT NOT NULL,
    data BLOB NOT NULL,
    miss_count INTEGER DEFAULT 0,
    cached_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    PRIMARY KEY (source, lookup_key)
);
CREATE INDEX IF NOT EXISTS idx_music_artists_expires ON music_artists(expires_at);

CREATE TABLE IF NOT EXISTS music_albums (
    source TEXT NOT NULL,
    lookup_key TEXT NOT NULL,
    data BLOB NOT NULL,
    miss_count INTEGER DEFAULT 0,
    cached_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    PRIMARY KEY (source, lookup_key)
);
CREATE INDEX IF NOT EXISTS idx_music_albums_expires ON music_albums(expires_at);

CREATE TABLE IF NOT EXISTS music_tracks (
    source TEXT NOT NULL,
    lookup_key TEXT NOT NULL,
    data BLOB NOT NULL,
    miss_count INTEGER DEFAULT 0,
    cached_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    PRIMARY KEY (source, lookup_key)
);
CREATE INDEX IF NOT EXISTS idx_music_tracks_expires ON music_tracks(expires_at);
"""

SOURCE_AUDIODB = 'audiodb'
SOURCE_LASTFM = 'lastfm'
SOURCE_WIKIPEDIA = 'wikipedia'

_SOURCE_MULTIPLIER = {
    SOURCE_AUDIODB: 0.5,
    SOURCE_LASTFM: 1.0,
    SOURCE_WIKIPEDIA: 1.0,
}

_AUDIODB_LANG_MAP = {
    'en': 'EN', 'es': 'ES', 'pt-br': 'PT', 'pt': 'PT',
    'fr': 'FR', 'de': 'DE', 'zh-cn': 'CN', 'zh-tw': 'CN',
    'it': 'IT', 'pl': 'PL', 'ru': 'RU', 'nl': 'NL',
    'sv': 'SE', 'ko': 'KR', 'ja': 'JA',
}


def audiodb_text_field(base: str) -> str:
    """Get language-specific AudioDB field name, e.g. 'strBiographyDE'."""
    from lib.kodi.settings import KodiSettings
    lang = KodiSettings.online_metadata_language()
    suffix = _AUDIODB_LANG_MAP.get(lang, 'EN')
    return f'{base}{suffix}'


def _artist_key(mbid: str, name: str) -> str:
    """Build lookup key for an artist: MBID if present, else lowercased name."""
    if mbid:
        return mbid
    return name.lower().strip()


def _album_key(mbid: str, artist: str, album: str) -> str:
    """Build lookup key for an album: MBID if present, else `artist\\0album` lowercased."""
    if mbid:
        return mbid
    return f"{artist}\0{album}".lower().strip()


def _track_key(artist: str, track: str) -> str:
    """Build lookup key for a track: `artist\\0track` lowercased."""
    return f"{artist}\0{track}".lower().strip()


def _apply_jitter(hours: float) -> int:
    """Multiply `hours` by a random 0.8-1.2 factor to spread cache expiry."""
    return max(1, int(hours * random.uniform(0.8, 1.2)))


def _miss_ttl_days(miss_count: int) -> int:
    """Exponential backoff for empty responses: 3, 6, 12, 24, 30 days."""
    return min(3 * (2 ** (miss_count - 1)), 30)


def _has_audiodb_text(data: dict, base: str) -> bool:
    """True if any language variant of an AudioDB text field is populated."""
    return any(data.get(f'{base}{suffix}') for suffix in set(_AUDIODB_LANG_MAP.values()))


def _has_artist_content(data: dict, source: str) -> bool:
    """True if artist response has usable bio/wiki content, not an empty shell."""
    if source == SOURCE_AUDIODB:
        return _has_audiodb_text(data, 'strBiography')
    bio = data.get('bio') or data.get('wiki')
    if isinstance(bio, dict):
        return bool(bio.get('content') or bio.get('summary'))
    return False


def _has_album_content(data: dict, source: str) -> bool:
    """True if album response has usable description/wiki content."""
    if source == SOURCE_AUDIODB:
        return _has_audiodb_text(data, 'strDescription')
    if source == SOURCE_WIKIPEDIA:
        return bool(data.get('summary'))
    wiki = data.get('wiki')
    if isinstance(wiki, dict):
        return bool(wiki.get('content') or wiki.get('summary'))
    return False


def _has_track_content(data: dict, source: str) -> bool:
    """True if track response has usable content (description, wiki, or toptags)."""
    if source == SOURCE_AUDIODB:
        return _has_audiodb_text(data, 'strDescription')
    if source == SOURCE_WIKIPEDIA:
        return bool(data.get('summary'))
    wiki = data.get('wiki')
    if isinstance(wiki, dict):
        return bool(wiki.get('content') or wiki.get('summary'))
    toptags = data.get('toptags')
    if isinstance(toptags, dict):
        tags = toptags.get('tag')
        if isinstance(tags, list) and tags:
            return True
    return False


def _artist_ttl_hours(data: dict, source: str, audiodb_artist: Optional[dict] = None) -> int:
    """Tiered TTL for artist data with content."""
    ref = audiodb_artist or (data if source == SOURCE_AUDIODB else None)

    base_days: int
    if ref:
        disbanded = ref.get('intDisbandedYear')
        died = ref.get('intDiedYear')
        if disbanded or died:
            base_days = 30
        else:
            formed = ref.get('intFormedYear')
            if formed:
                try:
                    years_active = datetime.now().year - int(formed)
                    base_days = 14 if years_active < 2 else 30
                except (ValueError, TypeError):
                    base_days = 30
            else:
                base_days = 30
    else:
        base_days = 14

    hours = base_days * 24 * _SOURCE_MULTIPLIER.get(source, 1.0)
    return _apply_jitter(hours)


def _album_ttl_hours(data: dict, source: str) -> int:
    """Tiered TTL for album data with content."""
    year_str = data.get('intYearReleased') or data.get('strReleaseDate') or ''
    if not year_str and source == SOURCE_LASTFM:
        # Last.fm doesn't have a top-level year; wiki might exist but no release date
        return _apply_jitter(14 * 24 * _SOURCE_MULTIPLIER.get(source, 1.0))

    try:
        if len(str(year_str)) == 4:
            release_date = datetime(int(year_str), 7, 1)
        else:
            release_date = datetime.fromisoformat(str(year_str))
        days_old = (datetime.now() - release_date).days
        base_days = 30 if days_old > 60 else 14
    except (ValueError, TypeError):
        base_days = 14

    hours = base_days * 24 * _SOURCE_MULTIPLIER.get(source, 1.0)
    return _apply_jitter(hours)


def _track_ttl_hours(source: str) -> int:
    """TTL for track data with content - flat 14 days."""
    hours = 14 * 24 * _SOURCE_MULTIPLIER.get(source, 1.0)
    return _apply_jitter(hours)


def init_music_database() -> None:
    """Create music metadata tables if missing."""
    with get_db(MUSIC_DB_PATH) as cursor:
        cursor.executescript(_SCHEMA_SQL)


def invalidate_music_cache(artist: str, track: str = '', album: str = '') -> int:
    """Delete cached entries for a specific artist/track/album combination.

    Removes all sources (Last.fm, Wikipedia, AudioDB) and all language variants.
    """
    total = 0
    with get_db(MUSIC_DB_PATH) as cursor:
        artist_lower = artist.lower().strip()
        if track:
            prefix = _track_key(artist, track)
            cursor.execute(
                "DELETE FROM music_tracks WHERE lookup_key = ? OR lookup_key LIKE ?",
                (prefix, prefix + ':%'),
            )
            total += cursor.rowcount
        if album:
            prefix = _album_key('', artist, album)
            cursor.execute(
                "DELETE FROM music_albums WHERE lookup_key = ? OR lookup_key LIKE ?",
                (prefix, prefix + ':%'),
            )
            total += cursor.rowcount
        if artist_lower:
            cursor.execute(
                "DELETE FROM music_artists WHERE lookup_key = ? OR lookup_key LIKE ?",
                (artist_lower, artist_lower + ':%'),
            )
            total += cursor.rowcount
    if total > 0:
        log("Database", "Invalidated {} music cache entries for '{}'".format(total, artist))
    return total


def clear_expired_music_cache() -> int:
    """Remove expired entries from all music cache tables. Returns total removed."""
    now = datetime.now().isoformat()
    total = 0
    with get_db(MUSIC_DB_PATH) as cursor:
        for table in ('music_artists', 'music_albums', 'music_tracks'):
            cursor.execute(f'DELETE FROM {table} WHERE expires_at < ?', (now,))
            total += cursor.rowcount
    if total > 0:
        log("Database", f"Cleared {total} expired music cache entries")
    return total


def _get_cached(table: str, source: str, lookup_key: str) -> Optional[dict]:
    """Fetch a cache row from `table`, return decompressed data or None if missing/expired."""
    with get_db(MUSIC_DB_PATH) as cursor:
        cursor.execute(
            f'SELECT data FROM {table} WHERE source = ? AND lookup_key = ? AND expires_at > ?',
            (source, lookup_key, datetime.now().isoformat()),
        )
        row = cursor.fetchone()
        if not row:
            return None
        try:
            return _decompress(row['data'])
        except Exception as e:
            log("Cache", f"Failed to decompress music cache ({table}): {e}", xbmc.LOGWARNING)
            return None


def _cache_entry(table: str, source: str, lookup_key: str, data: dict,
                 has_content: bool, ttl_hours: int) -> None:
    """Upsert a cache row. When `has_content` is False, applies exponential miss-backoff TTL."""
    now = datetime.now()

    with get_db(MUSIC_DB_PATH) as cursor:
        old_miss = 0
        if not has_content:
            cursor.execute(
                f'SELECT miss_count FROM {table} WHERE source = ? AND lookup_key = ?',
                (source, lookup_key),
            )
            row = cursor.fetchone()
            if row:
                old_miss = row['miss_count']

        if has_content:
            miss_count = 0
        else:
            miss_count = old_miss + 1
            ttl_hours = _miss_ttl_days(miss_count) * 24

        expires_at = now + timedelta(hours=ttl_hours)

        cursor.execute(
            f'''INSERT OR REPLACE INTO {table}
                (source, lookup_key, data, miss_count, cached_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)''',
            (source, lookup_key, _compress(data), miss_count,
             now.isoformat(), expires_at.isoformat()),
        )


def get_cached_artist(source: str, *, mbid: str = '', name: str = '',
                      lang: str = '') -> Optional[dict]:
    """Return cached artist data for the given `source` (audiodb/lastfm/wikipedia), or None."""
    key = _artist_key(mbid, name)
    if not key:
        return None
    if lang:
        key = f'{key}:{lang}'
    return _get_cached('music_artists', source, key)


def cache_artist(source: str, data: dict, *, mbid: str = '', name: str = '',
                 audiodb_artist: Optional[dict] = None, lang: str = '') -> None:
    """Cache artist data.

    When both `mbid` and `name` are given, writes under both keys so later name-only
    lookups hit (artist callers may resolve MBID after a name-only lookup). `cache_album`
    deliberately doesn't dual-write because its callers consistently pass `mbid` when known.
    """
    key = _artist_key(mbid, name)
    if not key:
        return
    if lang:
        key = f'{key}:{lang}'
    has_content = _has_artist_content(data, source)
    ttl = _artist_ttl_hours(data, source, audiodb_artist) if has_content else 0
    _cache_entry('music_artists', source, key, data, has_content, ttl)
    if mbid and name:
        name_key = name.lower().strip()
        if lang:
            name_key = f'{name_key}:{lang}'
        if name_key and name_key != key:
            _cache_entry('music_artists', source, name_key, data, has_content, ttl)


def get_cached_album(source: str, *, mbid: str = '', artist: str = '',
                     album: str = '', lang: str = '') -> Optional[dict]:
    """Return cached album data for the given source, or None."""
    key = _album_key(mbid, artist, album)
    if not key:
        return None
    if lang:
        key = f'{key}:{lang}'
    return _get_cached('music_albums', source, key)


def cache_album(source: str, data: dict, *, mbid: str = '', artist: str = '',
                album: str = '', lang: str = '') -> None:
    """Cache album data for the given source."""
    key = _album_key(mbid, artist, album)
    if not key:
        return
    if lang:
        key = f'{key}:{lang}'
    has_content = _has_album_content(data, source)
    ttl = _album_ttl_hours(data, source) if has_content else 0
    _cache_entry('music_albums', source, key, data, has_content, ttl)


def get_cached_track(source: str, artist: str, track: str, lang: str = '') -> Optional[dict]:
    """Return cached track data for the given source, or None."""
    key = _track_key(artist, track)
    if not key:
        return None
    if lang:
        key = f'{key}:{lang}'
    return _get_cached('music_tracks', source, key)


def cache_track(source: str, data: dict, artist: str, track: str, lang: str = '') -> None:
    """Cache track data for the given source."""
    key = _track_key(artist, track)
    if not key:
        return
    if lang:
        key = f'{key}:{lang}'
    has_content = _has_track_content(data, source)
    ttl = _track_ttl_hours(source) if has_content else 0
    _cache_entry('music_tracks', source, key, data, has_content, ttl)


def get_best_artist_bio(*, mbid: str = '', name: str = '') -> str:
    """Check AudioDB first (richer bios), fall back to Last.fm."""
    from lib.kodi.settings import KodiSettings
    lang = KodiSettings.online_metadata_language()
    suffix = _AUDIODB_LANG_MAP.get(lang, 'EN')

    audiodb_data = get_cached_artist(SOURCE_AUDIODB, mbid=mbid, name=name)
    if audiodb_data:
        bio = audiodb_data.get(f'strBiography{suffix}') or ''
        if not bio and suffix != 'EN':
            bio = audiodb_data.get('strBiographyEN') or ''
        if bio:
            return bio

    lastfm_data = get_cached_artist(SOURCE_LASTFM, mbid=mbid, name=name, lang=lang)
    if lastfm_data:
        bio_obj = lastfm_data.get('bio') or {}
        if isinstance(bio_obj, dict):
            content = bio_obj.get('content') or bio_obj.get('summary') or ''
            if content:
                href_idx = content.find('<a href=')
                if href_idx > 0:
                    content = content[:href_idx].rstrip()
                return content

    return ''
