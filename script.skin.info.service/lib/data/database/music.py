"""Music metadata cache: raw AudioDB, Last.fm and Wikipedia responses in `blob_cache`."""
from __future__ import annotations

import random
import time
from datetime import datetime
from typing import Optional, Final

import xbmc

from lib.data.database._infrastructure import (
    get_db,
    DB_PATH,
    sql_placeholders,
    compress_data as _compress,
    decompress_data as _decompress,
)
from lib.kodi.client import log

# a NUL here would truncate the bound LIKE pattern in invalidate_music_cache
_KEY_SEP: Final = '\x1f'

SOURCE_AUDIODB: Final = 'audiodb'
SOURCE_LASTFM: Final = 'lastfm'
SOURCE_WIKIPEDIA: Final = 'wikipedia'
SOURCE_MUSICBRAINZ: Final = 'musicbrainz'

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
    """Build lookup key for an album: MBID if present, else the lowercased artist and album."""
    if mbid:
        return mbid
    return f"{artist}{_KEY_SEP}{album}".lower().strip()


def _track_key(artist: str, track: str) -> str:
    """Build lookup key for a track: the lowercased artist and track."""
    return f"{artist}{_KEY_SEP}{track}".lower().strip()


def _apply_jitter(hours: float) -> int:
    """Apply a random 0.8-1.2 factor to spread cache expiry, never below an hour."""
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
    """TTL hours for artist data: 14 days for a young act or one AudioDB lacks, else 30."""
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
    """TTL hours for album data: 14 days for a recent or undated release, else 30."""
    year_str = data.get('intYearReleased') or data.get('strReleaseDate') or ''
    if not year_str and source == SOURCE_LASTFM:
        # Last.fm albums carry no release date
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
    """TTL hours for track data: 14 days."""
    hours = 14 * 24 * _SOURCE_MULTIPLIER.get(source, 1.0)
    return _apply_jitter(hours)


def _kind(entity: str, source: str) -> str:
    """`blob_cache.kind` for one music entity from one provider."""
    return f"music_{entity}_{source}"


def invalidate_music_cache(artist: str, track: str = '', album: str = '') -> int:
    """Invalidate cached entries for an artist, track or album across every source and language."""
    total = 0
    sources = (SOURCE_AUDIODB, SOURCE_LASTFM, SOURCE_WIKIPEDIA)
    with get_db(DB_PATH) as cursor:
        artist_lower = artist.lower().strip()
        targets = []
        if track:
            targets.append(('track', _track_key(artist, track)))
        if album:
            targets.append(('album', _album_key('', artist, album)))
        if artist_lower:
            targets.append(('artist', artist_lower))
        for entity, prefix in targets:
            kinds = [_kind(entity, src) for src in sources]
            placeholders = sql_placeholders(len(kinds))
            cursor.execute(
                f'DELETE FROM blob_cache WHERE kind IN ({placeholders}) '
                'AND (cache_key = ? OR cache_key LIKE ?)',
                (*kinds, prefix, prefix + ':%'),
            )
            total += cursor.rowcount
    if total > 0:
        log("Database", "Invalidated {} music cache entries for '{}'".format(total, artist))
    return total


def _get_cached(entity: str, source: str, lookup_key: str) -> Optional[dict]:
    """Cached blob for one entity, or None when missing or expired."""
    with get_db(DB_PATH) as cursor:
        cursor.execute(
            'SELECT data FROM blob_cache WHERE kind = ? AND cache_key = ? AND expires_at > ?',
            (_kind(entity, source), lookup_key, int(time.time())),
        )
        row = cursor.fetchone()
        if not row:
            return None
        try:
            return _decompress(row['data'])
        except Exception as e:
            log("Cache", f"Failed to decompress music cache ({entity}): {e}", xbmc.LOGWARNING)
            return None


def _cache_entry(entity: str, source: str, lookup_key: str, data: dict,
                 has_content: bool, ttl_hours: int) -> None:
    """Cache one row; an empty response gets an exponential miss-backoff TTL instead."""
    kind = _kind(entity, source)
    with get_db(DB_PATH) as cursor:
        miss_count = 0
        if not has_content:
            cursor.execute(
                'SELECT miss_count FROM blob_cache WHERE kind = ? AND cache_key = ?',
                (kind, lookup_key),
            )
            row = cursor.fetchone()
            miss_count = (row['miss_count'] if row else 0) + 1
            ttl_hours = _miss_ttl_days(miss_count) * 24

        cursor.execute(
            'INSERT INTO blob_cache (kind, cache_key, expires_at, miss_count, data) '
            'VALUES (?, ?, ?, ?, ?) '
            'ON CONFLICT (kind, cache_key) DO UPDATE SET '
            'expires_at = excluded.expires_at, miss_count = excluded.miss_count, '
            'data = excluded.data',
            (kind, lookup_key, int(time.time()) + ttl_hours * 3600, miss_count, _compress(data)),
        )


def get_cached_artist(source: str, *, mbid: str = '', name: str = '',
                      lang: str = '') -> Optional[dict]:
    """Get cached artist data from one source, or None."""
    key = _artist_key(mbid, name)
    if not key:
        return None
    if lang:
        key = f'{key}:{lang}'
    return _get_cached('artist', source, key)


def cache_artist(source: str, data: dict, *, mbid: str = '', name: str = '',
                 audiodb_artist: Optional[dict] = None, lang: str = '') -> None:
    """Cache artist data from one source, under the name key too when an MBID is given."""
    key = _artist_key(mbid, name)
    if not key:
        return
    if lang:
        key = f'{key}:{lang}'
    has_content = _has_artist_content(data, source)
    ttl = _artist_ttl_hours(data, source, audiodb_artist) if has_content else 0
    _cache_entry('artist', source, key, data, has_content, ttl)
    if mbid and name:
        name_key = name.lower().strip()
        if lang:
            name_key = f'{name_key}:{lang}'
        if name_key and name_key != key:
            _cache_entry('artist', source, name_key, data, has_content, ttl)


def get_cached_artist_list(entity: str, source: str, mbid: str) -> Optional[dict]:
    """Get a cached per-artist list, such as studio albums, from one source, or None."""
    return _get_cached(entity, source, mbid) if mbid else None


def cache_artist_list(entity: str, source: str, mbid: str, data: dict,
                      has_content: bool) -> None:
    """Cache a per-artist list for 30 days; an empty one backs off as a miss."""
    if mbid:
        _cache_entry(entity, source, mbid, data, has_content, _apply_jitter(30 * 24))


def get_cached_album(source: str, *, mbid: str = '', artist: str = '',
                     album: str = '', lang: str = '') -> Optional[dict]:
    """Get cached album data from one source, or None."""
    key = _album_key(mbid, artist, album)
    if not key:
        return None
    if lang:
        key = f'{key}:{lang}'
    return _get_cached('album', source, key)


def cache_album(source: str, data: dict, *, mbid: str = '', artist: str = '',
                album: str = '', lang: str = '') -> None:
    """Cache album data from one source."""
    key = _album_key(mbid, artist, album)
    if not key:
        return
    if lang:
        key = f'{key}:{lang}'
    has_content = _has_album_content(data, source)
    ttl = _album_ttl_hours(data, source) if has_content else 0
    _cache_entry('album', source, key, data, has_content, ttl)


def get_cached_track(source: str, artist: str, track: str, lang: str = '') -> Optional[dict]:
    """Get cached track data from one source, or None."""
    key = _track_key(artist, track)
    if not key:
        return None
    if lang:
        key = f'{key}:{lang}'
    return _get_cached('track', source, key)


def cache_track(source: str, data: dict, artist: str, track: str, lang: str = '') -> None:
    """Cache track data from one source."""
    key = _track_key(artist, track)
    if not key:
        return
    if lang:
        key = f'{key}:{lang}'
    has_content = _has_track_content(data, source)
    ttl = _track_ttl_hours(source) if has_content else 0
    _cache_entry('track', source, key, data, has_content, ttl)


def get_best_artist_bio(*, mbid: str = '', name: str = '') -> str:
    """Get the best cached artist bio, AudioDB before Last.fm, or '' when neither has one."""
    from lib.kodi.settings import KodiSettings
    lang = KodiSettings.online_metadata_language()

    audiodb_data = get_cached_artist(SOURCE_AUDIODB, mbid=mbid, name=name)
    if audiodb_data:
        bio = audiodb_data.get(audiodb_text_field('strBiography')) or ''
        if not bio:
            bio = audiodb_data.get('strBiographyEN') or ''
        if bio:
            return bio

    return lastfm_text(get_cached_artist(SOURCE_LASTFM, mbid=mbid, name=name, lang=lang))


def lastfm_text(data: Optional[dict]) -> str:
    """Wiki or bio text from a Last.fm response, cut before the link Last.fm appends."""
    if not isinstance(data, dict):
        return ''
    wiki = data.get('wiki') or data.get('bio')
    if not isinstance(wiki, dict):
        return ''
    content = wiki.get('content') or wiki.get('summary') or ''
    href_idx = content.find('<a href=')
    if href_idx > 0:
        content = content[:href_idx].rstrip()
    return content
