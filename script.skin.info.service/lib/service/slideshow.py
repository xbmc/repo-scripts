"""Rotating fanart backgrounds, published as window properties for the skin."""
from __future__ import annotations

import random
import threading
import time
import xbmc
import xbmcvfs
from collections import deque
from typing import Optional, Dict, Any, List, Final

from lib.data.database import slideshow as db_slideshow
from lib.data.slideshow import reconcile_pool
from lib.kodi.utilities import set_prop, clear_prop, get_prop
from lib.kodi.client import log, request

MIN_SLIDESHOW_INTERVAL: Final = 5
MAX_SLIDESHOW_INTERVAL: Final = 3600


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


# category -> ((skin property, pool row field), ...); an artist row's name is its title
_CATEGORY_PROPS = {
    'Movie': (('Title', 'title'), ('FanArt', 'fanart'), ('ClearLogo', 'clearlogo'),
              ('Plot', 'plot'), ('Year', 'year')),
    'TV': (('Title', 'title'), ('FanArt', 'fanart'), ('ClearLogo', 'clearlogo'),
           ('Plot', 'plot'), ('Year', 'year')),
    'Video': (('Title', 'title'), ('FanArt', 'fanart'), ('ClearLogo', 'clearlogo'),
              ('Plot', 'plot'), ('Year', 'year')),
    'Music': (('Artist', 'title'), ('FanArt', 'fanart'), ('ClearLogo', 'clearlogo'),
              ('Description', 'plot')),
    'MusicVideo': (('Title', 'title'), ('Artist', 'artist'), ('FanArt', 'fanart'),
                   ('ClearLogo', 'clearlogo'), ('Plot', 'plot'), ('Year', 'year')),
    'Global': (('Title', 'title'), ('FanArt', 'fanart'), ('ClearLogo', 'clearlogo'),
               ('Description', 'plot')),
}


def _clear_category_properties(category: str) -> None:
    """Clear one category's `SkinInfo.Slideshow.<category>.*` window props."""
    for prop, _field in _CATEGORY_PROPS.get(category, ()):
        clear_prop(f'SkinInfo.Slideshow.{category}.{prop}')


def clear_slideshow_properties() -> None:
    """Clear all `SkinInfo.Slideshow.*` window properties (called on service stop)."""
    for category in _CATEGORY_PROPS:
        _clear_category_properties(category)


_PLAYLIST_PREFIX: Final = 'SkinInfo.Slideshow.Playlist.'
_PLAYLIST_PATHS = _PLAYLIST_PREFIX + 'Paths'
_PLAYLIST_MUSIC_TYPES = {'song', 'album', 'artist'}
_PLAYLIST_SUFFIXES = ('Title', 'FanArt', 'ClearLogo', 'Plot', 'Year', 'Artist', 'Description')

# movie-set nodes report type 'unknown'; the id/fanart checks drop the rest of that bucket
_PLAYLIST_TYPES = frozenset(
    ('movie', 'tvshow', 'episode', 'musicvideo', 'set', 'song', 'album', 'artist', 'unknown'))

_PLAYLIST_PROPS = ['art', 'title', 'plot', 'year', 'firstaired', 'displayartist', 'description',
                   'artistid']

# episodes/songs/albums inherit fanart from the show/artist
_FANART_KEYS = ('fanart', 'tvshow.fanart', 'artist.fanart', 'albumartist.fanart')
_CLEARLOGO_KEYS = ('clearlogo', 'tvshow.clearlogo', 'artist.clearlogo', 'albumartist.clearlogo')

# items are held whole
_PLAYLIST_POOL_LIMIT: Final = 200

# a tiny or fanart-less pool wraps almost immediately
_PLAYLIST_REFETCH_MIN_S: Final = 60

LOOKAHEAD_DEPTH: Final = 2


def _item_art(item: Dict[str, Any], keys: tuple) -> str:
    """Art for a directory-listing item, falling back to its parent show/artist art."""
    art = item.get('art', {})
    for key in keys:
        url = art.get(key, '').strip()
        if url:
            return url
    return ''


def _artist_description(artist_id: Any) -> str:
    """Artist bio from the local pool, for a song/album carrying none of its own."""
    if isinstance(artist_id, list):
        artist_id = artist_id[0] if artist_id else None
    if not artist_id:
        return ''
    return db_slideshow.get_artist_description(int(artist_id))


def _year_of(detail: Dict[str, Any]) -> str:
    """Year from the item, falling back to the first-aired date."""
    year = detail.get('year')
    if year:
        return str(year)
    firstaired = detail.get('firstaired', '')
    return firstaired[:4] if firstaired[:4].isdigit() else ''


def _fetch_pool(path: str) -> list:
    """Fetch a path's items shuffled, with the fields a background needs; id-less ones dropped."""
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
    """Shuffled ref list with a fixed-depth lookahead; `pop` returns only entries resolved ahead."""

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
    """Rotates the backgrounds of skin-registered playlists, fanart cached two items ahead."""

    def __init__(self):
        self._slots: Dict[str, Dict[str, Any]] = {}
        self._known_names: set = set()
        self._invalidate = False

    def invalidate(self) -> None:
        """Re-fetch every slot's pool on the next refresh."""
        self._invalidate = True

    def refresh(self, abort_flag=None) -> None:
        """Rebuild on pool change, publish each category, refill lookahead. On the update thread."""
        if self._reconcile():
            self._refill(abort_flag)  # pre-fill (re)built slots so the first frame shows this tick
        self._display()
        self._refill(abort_flag)

    def clear(self) -> None:
        """Clear published props and drop the cursors."""
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
        """Reconcile the slideshow pool for one library kind."""
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
        """Advance every slot's cursor and publish the item it lands on."""
        for name, slot in self._slots.items():
            entry = slot['cursor'].pop()
            if entry is None:
                continue
            if entry['type'] in _PLAYLIST_MUSIC_TYPES:
                self._publish_music(name, entry)
            else:
                self._publish_video(name, entry)

    def _refill(self, abort_flag=None) -> None:
        """Force-cache each cursor's next fanart and clearlogo, then fill the lookaheads."""
        for slot in self._slots.values():
            cursor = slot['cursor']
            for item in cursor.wanted():
                if abort_flag and abort_flag.is_requested():
                    return
                cursor.deliver([self._resolve(item)])

    @staticmethod
    def _resolve(item: Dict[str, Any]) -> Optional[dict]:
        """Entry from a pool item; None if it has no fanart or its fanart fails to cache."""
        media_type = item.get('type', '')
        fanart = _item_art(item, _FANART_KEYS)
        if not fanart or not _cache_image_url(fanart):
            return None
        clearlogo = _item_art(item, _CLEARLOGO_KEYS)
        _cache_image_url(clearlogo)
        if media_type in _PLAYLIST_MUSIC_TYPES and not item.get('description'):
            item['description'] = _artist_description(item.get('artistid'))
        return {'type': media_type, 'detail': item, 'fanart': fanart, 'clearlogo': clearlogo}

    @staticmethod
    def _publish_video(name: str, entry: Dict[str, Any]) -> None:
        """Publish one playlist slot's video properties."""
        detail = entry['detail']
        prefix = f'{_PLAYLIST_PREFIX}{name}.'
        set_prop(prefix + 'Title', detail.get('title', '') or detail.get('label', ''))
        set_prop(prefix + 'FanArt', entry['fanart'])
        set_prop(prefix + 'ClearLogo', entry['clearlogo'])
        set_prop(prefix + 'Plot', detail.get('plot', ''))
        set_prop(prefix + 'Year', _year_of(detail))

    @staticmethod
    def _publish_music(name: str, entry: Dict[str, Any]) -> None:
        """Publish one playlist slot's music properties, preferring the display artist."""
        detail = entry['detail']
        prefix = f'{_PLAYLIST_PREFIX}{name}.'
        artist = detail.get('displayartist', '')
        if not artist:
            raw = detail.get('artist', '')
            artist = ' / '.join(raw) if isinstance(raw, list) else raw
        set_prop(prefix + 'Artist', artist or detail.get('label', ''))
        set_prop(prefix + 'FanArt', entry['fanart'])
        set_prop(prefix + 'ClearLogo', entry['clearlogo'])
        set_prop(prefix + 'Description', detail.get('description', ''))

    @staticmethod
    def _clear_name(name: str) -> None:
        """Clear every property of one playlist slot."""
        prefix = f'{_PLAYLIST_PREFIX}{name}.'
        for suffix in _PLAYLIST_SUFFIXES:
            clear_prop(prefix + suffix)


# category -> eligible pool types; a mixed category weights its type pick by pool size
_LIBRARY_CATEGORIES = {
    'Movie':      ('movie',),
    'TV':         ('tvshow',),
    'Music':      ('artist',),
    'MusicVideo': ('musicvideo',),
    'Video':      ('movie', 'tvshow'),
    'Global':     ('movie', 'tvshow', 'artist', 'musicvideo'),
}

# damping for the mixed-category type pick: 1.0 proportional to pool size, 0.0 equal
_WEIGHT_ALPHA: Final = 0.5


def _publish_library(category: str, row: Dict[str, Any]) -> None:
    """Publish one pool row as that category's `SkinInfo.Slideshow.*` properties."""
    for prop, field in _CATEGORY_PROPS[category]:
        value = row.get(field)
        set_prop(f'SkinInfo.Slideshow.{category}.{prop}', str(value) if value else '')


class LibrarySlideshow:
    """Rotates the library `SkinInfo.Slideshow.*` backgrounds, one shuffled cursor per type."""

    def __init__(self):
        self._generation = -1
        self._categories: Dict[str, Dict[str, _RotationCursor]] = {}
        self._weights: Dict[str, Dict[str, float]] = {}

    def refresh(self, abort_flag=None) -> None:
        """Rebuild on pool change, publish each category, refill lookahead. On the update thread."""
        rebuilt = db_slideshow.pool_generation() != self._generation
        if rebuilt:
            self._rebuild()
        if not self._categories:
            return
        if rebuilt:
            self._refill(abort_flag)
        self._display()
        self._refill(abort_flag)

    def clear(self) -> None:
        """Clear published props and drop the cursors."""
        clear_slideshow_properties()
        self._categories = {}
        self._weights = {}
        self._generation = -1

    def _rebuild(self) -> None:
        """Rebuild the rotation cursors from the pool, clearing categories that no longer fill."""
        self._generation = db_slideshow.pool_generation()
        pool: Dict[str, list] = {}
        for row in db_slideshow.get_all_pool_rows():
            pool.setdefault(row['media_type'], []).append(dict(row))

        previous = set(self._categories)
        self._categories = {}
        self._weights = {}
        for category, types in _LIBRARY_CATEGORIES.items():
            cursors = {t: _RotationCursor(random.sample(pool[t], len(pool[t])))
                       for t in types if pool.get(t)}
            if cursors:
                self._categories[category] = cursors
                self._weights[category] = {t: len(pool[t]) ** _WEIGHT_ALPHA for t in cursors}

        for category in previous - set(self._categories):
            _clear_category_properties(category)

    def _pick_type(self, category: str, cursors: Dict[str, _RotationCursor]) -> Optional[str]:
        """Pick a ready media type for the category, weighted by pool size."""
        ready = [t for t in cursors if cursors[t].has_ready()]
        if not ready:
            return None
        if len(ready) == 1:
            return ready[0]
        weights = self._weights[category]
        return random.choices(ready, weights=[weights[t] for t in ready])[0]

    def _display(self) -> None:
        """Publish one item per category, picking a type from that category's pool."""
        for category, cursors in self._categories.items():
            media_type = self._pick_type(category, cursors)
            if not media_type:
                continue
            entry = cursors[media_type].pop()
            if entry is not None:
                _publish_library(category, entry)

    def _refill(self, abort_flag=None) -> None:
        """Force-cache each cursor's next fanart and clearlogo, then fill the lookaheads."""
        for cursors in self._categories.values():
            for cursor in cursors.values():
                for row in cursor.wanted():
                    if abort_flag and abort_flag.is_requested():
                        return
                    if not _cache_image_url(row.get('fanart', '')):
                        cursor.deliver([None])
                        continue
                    _cache_image_url(row.get('clearlogo') or '')
                    cursor.deliver([row])


class SlideshowMonitor(xbmc.Monitor):
    """Reconciles the pool for the library a scan or clean just changed, off the callback thread."""

    def _reconcile(self, library: str, reason: str) -> None:
        """Reconcile the slideshow pool for one library kind."""
        scope = ('artist',) if library == 'music' else ('movie', 'tvshow', 'musicvideo')
        try:
            log("Service", f"Slideshow: {reason}, reconciling {scope}...", xbmc.LOGDEBUG)
            from lib.infrastructure.tasks import ShutdownAbortFlag
            reconcile_pool(scope, ShutdownAbortFlag())
        except Exception as e:
            log("Service", f"Slideshow: Error reconciling pool: {e}", xbmc.LOGERROR)

    def onScanFinished(self, library: str) -> None:
        """Reconcile the scanned library's pool types."""
        threading.Thread(target=self._reconcile,
                         args=(library, f"Library scan finished ({library})"), daemon=True).start()

    def onCleanFinished(self, library: str) -> None:
        """Reconcile the cleaned library's pool types."""
        threading.Thread(target=self._reconcile,
                         args=(library, f"Library clean finished ({library})"), daemon=True).start()
