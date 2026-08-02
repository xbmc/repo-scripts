"""Slideshow functionality for rotating fanart backgrounds.

Provides window properties with random fanart from library for skin slideshows.
"""
from __future__ import annotations

import random
import threading
import time
import xbmc
import xbmcvfs
from collections import deque
from typing import Optional, Dict, Any, List

from lib.data.database import slideshow as db_slideshow
from lib.kodi.utilities import set_prop, clear_prop, get_prop
from lib.kodi.client import log, request, get_item_details

MIN_SLIDESHOW_INTERVAL = 5
MAX_SLIDESHOW_INTERVAL = 3600


def _cache_image_url(url: str) -> bool:
    """Force Kodi to cache an image URL by reading it via `xbmcvfs.File`; True on success."""
    if not url:
        return False

    from lib.kodi.client import encode_image_url
    wrapped_url = encode_image_url(url) if not url.startswith('image://') else url

    try:
        f = xbmcvfs.File(wrapped_url)
        cached = f.size() > 0
        f.close()
        return cached
    except Exception as e:
        log("Service", f"Slideshow: Failed to cache URL {url}: {e}", xbmc.LOGWARNING)
        return False


def _build_pool_records(media_type: str, items: list, id_key: str, title_key: str,
                        fanart_key: str, description_key: str, current_time: int) -> List[tuple]:
    records = []
    for item in items:
        dbid = item.get(id_key)
        if not dbid:
            continue
        if media_type == 'artist':
            fanart = item.get(fanart_key, '')
            year = None
        else:
            fanart = item.get('art', {}).get(fanart_key, '')
            year = item.get('year')

        records.append((
            dbid,
            media_type,
            item.get(title_key, ''),
            fanart,
            item.get(description_key, ''),
            year,
            None,
            None,
            current_time
        ))
    return records


def populate_slideshow_pool() -> None:
    """Rebuild slideshow_pool from the library (movies/tvshows/artists with fanart)."""
    current_time = int(time.time())

    movies = _get_movies_with_fanart()
    tvshows = _get_tvshows_with_fanart()
    artists = _get_artists_with_fanart()
    if movies is None or tvshows is None or artists is None:
        log("Service", "Slideshow: a library fetch failed, skipping populate to avoid wiping pool",
            xbmc.LOGWARNING)
        return

    movie_records = _build_pool_records(
        'movie', movies, 'movieid', 'title', 'fanart', 'plot', current_time
    )
    tvshow_records = _build_pool_records(
        'tvshow', tvshows, 'tvshowid', 'title', 'fanart', 'plot', current_time
    )
    artist_records = _build_pool_records(
        'artist', artists, 'artistid', 'artist', 'fanart', 'description', current_time
    )

    db_slideshow.populate_pool(movie_records, tvshow_records, artist_records)

    log("Service",
        f"Slideshow: Pool populated with {len(movies)} movies, {len(tvshows)} TV shows, "
        f"{len(artists)} artists")


_RECONCILE_LOCK = threading.Lock()


def reconcile_pool(scope: tuple) -> None:
    """Diff the pool against the current library for `scope` media types; apply only changes.

    Bumps the pool generation only when something differs, so an unchanged pass causes no cursor
    reshuffle. A scope whose library fetch fails is left untouched (its rows are NOT deleted), so a
    transient JSON-RPC failure can't wipe the pool. Serialised so the scan and idle reconcile
    paths never run concurrently. `scope` is e.g. ('movie','tvshow'), ('artist',), or all three.
    """
    with _RECONCILE_LOCK:
        fetchers = {
            'movie':  (_get_movies_with_fanart,  'movieid',  'title',  'plot'),
            'tvshow': (_get_tvshows_with_fanart, 'tvshowid', 'title',  'plot'),
            'artist': (_get_artists_with_fanart, 'artistid', 'artist', 'description'),
        }
        current_time = int(time.time())
        desired = {}
        fetched = set()
        for mtype in scope:
            getter, id_key, title_key, desc_key = fetchers[mtype]
            items = getter()
            if items is None:  # fetch failed - keep this type's rows, don't diff/delete them
                continue
            fetched.add(mtype)
            for rec in _build_pool_records(mtype, items, id_key, title_key, 'fanart', desc_key,
                                           current_time):
                desired[(rec[1], rec[0])] = rec

        existing = db_slideshow.get_pool_compare_fields(scope)
        upserts = [rec for key, rec in desired.items()
                   if (rec[2], rec[3], rec[4], rec[5]) != existing.get(key)]
        deletes = [key for key in existing if key not in desired and key[0] in fetched]
        db_slideshow.apply_pool_diff(upserts, deletes)


_POOL_MEDIA_TYPES = ('movie', 'tvshow', 'artist')

_DETAIL_PROPS = {
    'movie':  ['art', 'title', 'plot', 'year'],
    'tvshow': ['art', 'title', 'plot', 'year'],
    'artist': ['art', 'description'],
}


def refresh_pool_item(media_type: str, dbid: int) -> None:
    """Sync one item's slideshow-pool row to its current library art (after an in-app art change).

    Upserts if it now has fanart, drops the row otherwise. No-op for media the pool doesn't track.
    """
    if media_type not in _POOL_MEDIA_TYPES:
        return

    detail = get_item_details(media_type, dbid, _DETAIL_PROPS[media_type])
    if not isinstance(detail, dict):
        return

    fanart = _detail_fanart(detail)
    if not fanart:
        db_slideshow.delete_pool_item(media_type, dbid)
        return

    if media_type == 'artist':
        title = detail.get('label', '')
        description = detail.get('description', '')
        year = None
    else:
        title = detail.get('title', '')
        description = detail.get('plot', '')
        year = detail.get('year')

    db_slideshow.upsert_pool_item(media_type, dbid, title, fanart, description, year,
                                  int(time.time()))


def _get_movies_with_fanart() -> Optional[list]:
    """Movies with fanart, or None if the library fetch failed (vs [] = none have fanart)."""
    response = request("VideoLibrary.GetMovies", {
        "properties": ["title", "art", "year", "plot"]
    })
    if response is None:
        return None
    return [m for m in response.get('result', {}).get('movies', [])
            if m.get('art', {}).get('fanart', '').strip()]


def _get_tvshows_with_fanart() -> Optional[list]:
    """TV shows with fanart, or None if the library fetch failed (vs [] = none have fanart)."""
    response = request("VideoLibrary.GetTVShows", {
        "properties": ["title", "art", "year", "plot"]
    })
    if response is None:
        return None
    return [s for s in response.get('result', {}).get('tvshows', [])
            if s.get('art', {}).get('fanart', '').strip()]


def _get_artists_with_fanart() -> Optional[list]:
    """Artists with fanart, or None if the library fetch failed (vs [] = none have fanart)."""
    response = request("AudioLibrary.GetArtists", {
        "properties": ["fanart", "description"]
    })

    if response is None:
        return None

    all_artists = response.get('result', {}).get('artists', [])

    artists_with_fanart = []

    for artist in all_artists:
        fanart = artist.get('fanart', '').strip()

        if fanart:
            artists_with_fanart.append({
                'artistid': artist.get('artistid'),
                'artist': artist.get('artist', ''),
                'fanart': fanart,
                'description': artist.get('description', '')
            })

    log("Service", f"Slideshow: Found {len(artists_with_fanart)} artists with fanart")
    return artists_with_fanart


def set_movie_slideshow_properties(item: Dict[str, Any]) -> None:
    """Set SkinInfo.Slideshow.Movie.* properties."""
    set_prop('SkinInfo.Slideshow.Movie.Title', item.get('title', ''))
    set_prop('SkinInfo.Slideshow.Movie.FanArt', item.get('fanart', ''))
    set_prop('SkinInfo.Slideshow.Movie.Plot', item.get('plot', ''))
    set_prop('SkinInfo.Slideshow.Movie.Year', str(item.get('year', '')) if item.get('year') else '')


def set_tv_slideshow_properties(item: Dict[str, Any]) -> None:
    """Set SkinInfo.Slideshow.TV.* properties."""
    set_prop('SkinInfo.Slideshow.TV.Title', item.get('title', ''))
    set_prop('SkinInfo.Slideshow.TV.FanArt', item.get('fanart', ''))
    set_prop('SkinInfo.Slideshow.TV.Plot', item.get('plot', ''))
    set_prop('SkinInfo.Slideshow.TV.Year', str(item.get('year', '')) if item.get('year') else '')


def set_video_slideshow_properties(item: Dict[str, Any]) -> None:
    """Set SkinInfo.Slideshow.Video.* properties."""
    set_prop('SkinInfo.Slideshow.Video.Title', item.get('title', ''))
    set_prop('SkinInfo.Slideshow.Video.FanArt', item.get('fanart', ''))
    set_prop('SkinInfo.Slideshow.Video.Plot', item.get('plot', ''))
    set_prop('SkinInfo.Slideshow.Video.Year', str(item.get('year', '')) if item.get('year') else '')


def set_music_slideshow_properties(item: Dict[str, Any]) -> None:
    """Set SkinInfo.Slideshow.Music.* properties."""
    set_prop('SkinInfo.Slideshow.Music.Artist', item.get('artist', ''))
    set_prop('SkinInfo.Slideshow.Music.FanArt', item.get('fanart', ''))
    set_prop('SkinInfo.Slideshow.Music.Description', item.get('description', ''))


def set_global_slideshow_properties(item: Dict[str, Any]) -> None:
    """Set SkinInfo.Slideshow.Global.* properties."""
    set_prop('SkinInfo.Slideshow.Global.Title', item.get('title', ''))
    set_prop('SkinInfo.Slideshow.Global.FanArt', item.get('fanart', ''))
    set_prop('SkinInfo.Slideshow.Global.Description', item.get('description', ''))


def is_pool_populated() -> bool:
    """Check if slideshow pool has any items."""
    return db_slideshow.is_pool_populated()


_CATEGORY_PROPS = {
    'Movie': ('Title', 'FanArt', 'Plot', 'Year'),
    'TV': ('Title', 'FanArt', 'Plot', 'Year'),
    'Video': ('Title', 'FanArt', 'Plot', 'Year'),
    'Music': ('Artist', 'FanArt', 'Description'),
    'Global': ('Title', 'FanArt', 'Description'),
}


def _clear_category_properties(category: str) -> None:
    """Clear one category's `SkinInfo.Slideshow.<category>.*` window props."""
    for prop in _CATEGORY_PROPS.get(category, ()):
        clear_prop(f'SkinInfo.Slideshow.{category}.{prop}')


def clear_slideshow_properties() -> None:
    """Clear all `SkinInfo.Slideshow.*` window properties (called on service stop)."""
    for category in _CATEGORY_PROPS:
        _clear_category_properties(category)


_PLAYLIST_PREFIX = 'SkinInfo.Slideshow.Playlist.'
_PLAYLIST_PATHS = _PLAYLIST_PREFIX + 'Paths'
_PLAYLIST_MUSIC_TYPES = {'song', 'album', 'artist'}
_PLAYLIST_SUFFIXES = ('Title', 'FanArt', 'Plot', 'Year', 'Artist', 'Description')

# movie-set nodes report type 'unknown'; the id/fanart checks drop the rest of that bucket
_PLAYLIST_TYPES = frozenset(
    ('movie', 'tvshow', 'episode', 'musicvideo', 'set', 'song', 'album', 'artist', 'unknown'))

_PLAYLIST_PROPS = ['art', 'title', 'plot', 'year', 'firstaired', 'displayartist', 'description',
                   'artistid']

# episodes/songs/albums inherit fanart from the show/artist
_FANART_KEYS = ('fanart', 'tvshow.fanart', 'artist.fanart', 'albumartist.fanart')

# items are held whole
_PLAYLIST_POOL_LIMIT = 200

# a tiny or fanart-less pool wraps almost immediately
_PLAYLIST_REFETCH_MIN_S = 60

LOOKAHEAD_DEPTH = 2


def _detail_fanart(detail: Dict[str, Any]) -> str:
    return (detail.get('art', {}).get('fanart', '') or detail.get('fanart', '')).strip()


def _item_fanart(item: Dict[str, Any]) -> str:
    """Fanart for a directory-listing item, falling back to its parent show/artist art."""
    art = item.get('art', {})
    for key in _FANART_KEYS:
        fanart = art.get(key, '').strip()
        if fanart:
            return fanart
    return ''


def _artist_description(artist_id: Any) -> str:
    """Artist bio from the local pool, for a song/album carrying none of its own."""
    if isinstance(artist_id, list):
        artist_id = artist_id[0] if artist_id else None
    if not artist_id:
        return ''
    return db_slideshow.get_artist_description(int(artist_id))


def _year_of(detail: Dict[str, Any]) -> str:
    year = detail.get('year')
    if year:
        return str(year)
    firstaired = detail.get('firstaired', '')
    return firstaired[:4] if firstaired[:4].isdigit() else ''


def _fetch_pool(path: str) -> list:
    """Randomised items for `path` with the properties a background needs; id-less items dropped."""
    response = request("Files.GetDirectory", {
        "directory": path,
        "media": "files",
        "properties": _PLAYLIST_PROPS,
        "sort": {"method": "random"},
        "limits": {"start": 0, "end": _PLAYLIST_POOL_LIMIT},
    })
    files = response.get('result', {}).get('files', []) if response else []
    return [f for f in files if f.get('type') in _PLAYLIST_TYPES and f.get('id')]


class _RotationCursor:
    """Shuffled ref list with a fixed-depth lookahead of resolved entries.

    The owner resolves refs out-of-band (image caching blocks); `pop()` only returns an
    already-cached entry.
    """

    def __init__(self, refs: list, depth: int = LOOKAHEAD_DEPTH):
        self._refs = refs
        self._cursor = 0
        self._depth = depth
        self._ready: deque = deque()

    def __bool__(self) -> bool:
        return bool(self._refs)

    def wanted(self) -> list:
        """Refs to resolve to refill the lookahead to its depth, advancing the cursor."""
        out = []
        need = self._depth - len(self._ready)
        while need > 0 and self._refs:
            out.append(self._refs[self._cursor % len(self._refs)])
            self._cursor += 1
            need -= 1
        return out

    def deliver(self, entries: list) -> None:
        """Append resolved entries; None means unresolved/no-fanart and is skipped."""
        for entry in entries:
            if entry is not None:
                self._ready.append(entry)

    def has_ready(self) -> bool:
        """True if a resolved entry is queued for display this tick."""
        return bool(self._ready)

    def wrapped(self) -> bool:
        """True once the whole shuffled list has been handed out."""
        return bool(self._refs) and self._cursor >= len(self._refs)

    def pop(self):
        """Next ready entry, or None if the lookahead is empty this tick."""
        return self._ready.popleft() if self._ready else None


class PlaylistRotator:
    """Rotates skin-registered playlist backgrounds by menu-item name.

    Holds each slot's whole pool, re-fetched when it wraps; fanart is force-cached 2-ahead so a
    fade lands on a cached image.
    """

    def __init__(self):
        self._slots: Dict[str, Dict[str, Any]] = {}
        self._known_names: set = set()
        self._invalidate = False

    def invalidate(self) -> None:
        """Re-fetch every slot's pool on the next refresh."""
        self._invalidate = True

    def refresh(self) -> None:
        """Reconcile slots, publish current items, refill the lookahead. On the update thread."""
        if self._reconcile():
            self._refill()  # pre-fill (re)built slots so the first frame shows this tick
        self._display()
        self._refill()

    def clear(self) -> None:
        """Clear published props and drop the slots."""
        for name in self._known_names:
            self._clear_name(name)
        self._slots = {}
        self._known_names = set()

    def _registry(self) -> List[tuple]:
        """Parse the `name=path|name=path|` manifest into (name, path) pairs."""
        pairs = []
        for token in get_prop(_PLAYLIST_PATHS).split('|'):
            name, sep, path = token.partition('=')
            name, path = name.strip(), path.strip()
            if sep and name and path:
                pairs.append((name, path))
        return pairs

    def _reconcile(self) -> bool:
        """Rebuild changed, new and exhausted slots. Returns True if any slot was (re)built."""
        invalidate = self._invalidate
        self._invalidate = False
        rebuilt = False

        now = time.time()
        new_slots: Dict[str, Dict[str, Any]] = {}
        for name, path in self._registry():
            existing = self._slots.get(name)
            if (existing and existing['path'] == path and not invalidate
                    and not self._needs_refetch(existing, now)):
                new_slots[name] = existing
                continue
            new_slots[name] = {'path': path, 'built': now,
                               'cursor': _RotationCursor(_fetch_pool(path))}
            rebuilt = True

        for name in self._known_names - set(new_slots):
            self._clear_name(name)

        self._slots = new_slots
        self._known_names = set(new_slots)
        return rebuilt

    @staticmethod
    def _needs_refetch(slot: Dict[str, Any], now: float) -> bool:
        """True if a slot's pool is spent, or empty because its fetch failed."""
        if now - slot['built'] < _PLAYLIST_REFETCH_MIN_S:
            return False
        cursor = slot['cursor']
        return cursor.wrapped() or not cursor

    def _display(self) -> None:
        for name, slot in self._slots.items():
            entry = slot['cursor'].pop()
            if entry is None:
                continue
            if entry['type'] in _PLAYLIST_MUSIC_TYPES:
                self._publish_music(name, entry)
            else:
                self._publish_video(name, entry)

    def _refill(self) -> None:
        """Force-cache each slot's next fanart and fill the lookaheads."""
        for slot in self._slots.values():
            cursor = slot['cursor']
            for item in cursor.wanted():
                cursor.deliver([self._resolve(item)])

    @staticmethod
    def _resolve(item: Dict[str, Any]) -> Optional[dict]:
        """Entry from a pool item; None if it has no fanart or caching fails."""
        media_type = item.get('type', '')
        fanart = _item_fanart(item)
        if not fanart or not _cache_image_url(fanart):
            return None
        if media_type in _PLAYLIST_MUSIC_TYPES and not item.get('description'):
            item['description'] = _artist_description(item.get('artistid'))
        return {'type': media_type, 'detail': item, 'fanart': fanart}

    @staticmethod
    def _publish_video(name: str, entry: Dict[str, Any]) -> None:
        detail = entry['detail']
        prefix = f'{_PLAYLIST_PREFIX}{name}.'
        set_prop(prefix + 'Title', detail.get('title', '') or detail.get('label', ''))
        set_prop(prefix + 'FanArt', entry['fanart'])
        set_prop(prefix + 'Plot', detail.get('plot', ''))
        set_prop(prefix + 'Year', _year_of(detail))

    @staticmethod
    def _publish_music(name: str, entry: Dict[str, Any]) -> None:
        detail = entry['detail']
        prefix = f'{_PLAYLIST_PREFIX}{name}.'
        artist = detail.get('displayartist', '')
        if not artist:
            raw = detail.get('artist', '')
            artist = ' / '.join(raw) if isinstance(raw, list) else raw
        set_prop(prefix + 'Artist', artist or detail.get('label', ''))
        set_prop(prefix + 'FanArt', entry['fanart'])
        set_prop(prefix + 'Description', detail.get('description', ''))

    @staticmethod
    def _clear_name(name: str) -> None:
        prefix = f'{_PLAYLIST_PREFIX}{name}.'
        for suffix in _PLAYLIST_SUFFIXES:
            clear_prop(prefix + suffix)


# category -> (publish style, eligible types). Mixed categories (Video/Global) weight the
# type pick by pool size; see LibrarySlideshow.
_LIBRARY_CATEGORIES = {
    'Movie':  ('video',  ('movie',)),
    'TV':     ('video',  ('tvshow',)),
    'Music':  ('music',  ('artist',)),
    'Video':  ('video',  ('movie', 'tvshow')),
    'Global': ('global', ('movie', 'tvshow', 'artist')),
}

_CATEGORY_PUBLISHERS = {
    'Movie':  set_movie_slideshow_properties,
    'TV':     set_tv_slideshow_properties,
    'Music':  set_music_slideshow_properties,
    'Video':  set_video_slideshow_properties,
    'Global': set_global_slideshow_properties,
}

# sqrt damping for mixed-category type weighting: 1.0 = proportional, 0.0 = equal.
_WEIGHT_ALPHA = 0.5


def _publish_library(category: str, row: Dict[str, Any]) -> None:
    style = _LIBRARY_CATEGORIES[category][0]
    publisher = _CATEGORY_PUBLISHERS[category]
    fanart = row.get('fanart', '')
    if style == 'music':
        publisher({'artist': row.get('title', ''), 'fanart': fanart,
                   'description': row.get('description', '')})
    elif style == 'global':
        publisher({'title': row.get('title', ''), 'fanart': fanart,
                   'description': row.get('description', '')})
    else:
        publisher({'title': row.get('title', ''), 'fanart': fanart,
                   'plot': row.get('description', ''), 'year': row.get('year')})


class LibrarySlideshow:
    """Rotates the library-wide `SkinInfo.Slideshow.*` backgrounds from the DB pool.

    Independent shuffled cursor per type per category (so categories never sync); mixed
    Video/Global pick a type weighted by `count ** alpha`. 2-ahead lookahead; cursors rebuild
    on pool-generation change.
    """

    def __init__(self):
        self._generation = -1
        self._categories: Dict[str, Dict[str, _RotationCursor]] = {}
        self._weights: Dict[str, Dict[str, float]] = {}

    def refresh(self) -> None:
        """Rebuild on pool change, publish each category, refill lookahead. On the update thread."""
        rebuilt = db_slideshow.pool_generation() != self._generation
        if rebuilt:
            self._rebuild()
        if not self._categories:
            return
        if rebuilt:
            self._refill()  # pre-fill new cursors so the first frame shows this tick
        self._display()
        self._refill()

    def clear(self) -> None:
        """Clear published props and drop the cursors."""
        clear_slideshow_properties()
        self._categories = {}
        self._weights = {}
        self._generation = -1

    def _rebuild(self) -> None:
        self._generation = db_slideshow.pool_generation()
        pool: Dict[str, list] = {}
        for row in db_slideshow.get_all_pool_rows():
            pool.setdefault(row['media_type'], []).append(dict(row))

        previous = set(self._categories)
        self._categories = {}
        self._weights = {}
        for category, spec in _LIBRARY_CATEGORIES.items():
            types = spec[1]
            cursors = {t: _RotationCursor(random.sample(pool[t], len(pool[t])))
                       for t in types if pool.get(t)}
            if cursors:
                self._categories[category] = cursors
                self._weights[category] = {t: len(pool[t]) ** _WEIGHT_ALPHA for t in cursors}

        for category in previous - set(self._categories):
            _clear_category_properties(category)

    def _pick_type(self, category: str, cursors: Dict[str, _RotationCursor]) -> Optional[str]:
        ready = [t for t in cursors if cursors[t].has_ready()]
        if not ready:
            return None
        if len(ready) == 1:
            return ready[0]
        weights = self._weights[category]
        return random.choices(ready, weights=[weights[t] for t in ready])[0]

    def _display(self) -> None:
        for category, cursors in self._categories.items():
            media_type = self._pick_type(category, cursors)
            if not media_type:
                continue
            entry = cursors[media_type].pop()
            if entry is not None:
                _publish_library(category, entry)

    def _refill(self) -> None:
        for cursors in self._categories.values():
            for cursor in cursors.values():
                for row in cursor.wanted():
                    cursor.deliver([row if _cache_image_url(row.get('fanart', '')) else None])


class SlideshowMonitor(xbmc.Monitor):
    """Reconciles the slideshow pool against the library on scan/clean, scoped to the changed type.

    Runs on a daemon thread: the reconcile does library JSON-RPC reads that would otherwise
    block the Monitor callback thread for seconds. `reconcile_pool` self-serialises against the
    idle reconcile, so back-to-back scan/clean events are handled safely.
    """

    def _reconcile(self, library: str, reason: str) -> None:
        scope = ('artist',) if library == 'music' else ('movie', 'tvshow')
        try:
            log("Service", f"Slideshow: {reason}, reconciling {scope}...", xbmc.LOGDEBUG)
            reconcile_pool(scope)
        except Exception as e:
            log("Service", f"Slideshow: Error reconciling pool: {e}", xbmc.LOGERROR)

    def onScanFinished(self, library: str) -> None:
        threading.Thread(target=self._reconcile,
                         args=(library, f"Library scan finished ({library})"), daemon=True).start()

    def onCleanFinished(self, library: str) -> None:
        threading.Thread(target=self._reconcile,
                         args=(library, f"Library clean finished ({library})"), daemon=True).start()
