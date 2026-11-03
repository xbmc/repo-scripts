"""Slideshow pool upkeep: builds the pool from the library and keeps it in step with art changes."""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

import xbmc

from lib.data.database import slideshow as db_slideshow
from lib.kodi.client import log, request, get_item_details


def _build_pool_records(media_type: str, items: list, id_key: str, title_key: str,
                        fanart_key: str, plot_key: str) -> List[tuple]:
    """Build pool table rows from library items; artists carry fanart outside the art dict."""
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
            media_type,
            dbid,
            item.get(title_key, ''),
            fanart,
            item.get(plot_key, ''),
            year,
            _joined_artist(item.get('artist')) if media_type == 'musicvideo' else '',
            item.get('art', {}).get('clearlogo', '')
        ))
    return records


def _joined_artist(artist: Any) -> str:
    """Music video artist names as one string; Kodi stores them as a list."""
    if isinstance(artist, list):
        return ', '.join(a for a in artist if a)
    return artist or ''


def populate_slideshow_pool() -> None:
    """Rebuild slideshow_pool from the library (movies/tvshows/artists/music videos with fanart)."""
    movies = _get_movies_with_fanart()
    tvshows = _get_tvshows_with_fanart()
    artists = _get_artists_with_fanart()
    musicvideos = _get_musicvideos_with_fanart()
    if movies is None or tvshows is None or artists is None or musicvideos is None:
        log("Service", "Slideshow: a library fetch failed, skipping populate to avoid wiping pool",
            xbmc.LOGWARNING)
        return

    movie_records = _build_pool_records('movie', movies, 'movieid', 'title', 'fanart', 'plot')
    tvshow_records = _build_pool_records('tvshow', tvshows, 'tvshowid', 'title', 'fanart', 'plot')
    artist_records = _build_pool_records(
        'artist', artists, 'artistid', 'artist', 'fanart', 'description')
    musicvideo_records = _build_pool_records(
        'musicvideo', musicvideos, 'musicvideoid', 'title', 'fanart', 'plot')

    db_slideshow.populate_pool(movie_records, tvshow_records, artist_records, musicvideo_records)

    log("Service",
        f"Slideshow: Pool populated with {len(movies)} movies, {len(tvshows)} TV shows, "
        f"{len(artists)} artists, {len(musicvideos)} music videos")


_RECONCILE_LOCK = threading.Lock()


def reconcile_pool(scope: tuple, abort_flag=None) -> None:
    """Diff the pool against the library, apply only changes; a failed fetch skips its scope."""
    with _RECONCILE_LOCK:
        fetchers = {
            'movie':      (_get_movies_with_fanart,      'movieid',      'title',  'plot'),
            'tvshow':     (_get_tvshows_with_fanart,     'tvshowid',     'title',  'plot'),
            'artist':     (_get_artists_with_fanart,     'artistid',     'artist', 'description'),
            'musicvideo': (_get_musicvideos_with_fanart, 'musicvideoid', 'title',  'plot'),
        }
        desired = {}
        fetched = set()
        for mtype in scope:
            getter, id_key, title_key, plot_key = fetchers[mtype]
            items = getter()
            if abort_flag and abort_flag.is_requested():
                return
            if items is None:
                continue
            fetched.add(mtype)
            for rec in _build_pool_records(mtype, items, id_key, title_key, 'fanart', plot_key):
                desired[(rec[0], rec[1])] = rec

        existing = db_slideshow.get_pool_compare_fields(scope)
        upserts = [rec for key, rec in desired.items()
                   if rec[2:] != existing.get(key)]
        deletes = [key for key in existing if key not in desired and key[0] in fetched]
        db_slideshow.apply_pool_diff(upserts, deletes)


POOL_MEDIA_TYPES = ('movie', 'tvshow', 'artist', 'musicvideo')


_DETAIL_PROPS = {
    'movie':      ['art', 'title', 'plot', 'year'],
    'tvshow':     ['art', 'title', 'plot', 'year'],
    'artist':     ['art', 'description'],
    'musicvideo': ['art', 'title', 'plot', 'year', 'artist'],
}


def _detail_fanart(detail: Dict[str, Any]) -> str:
    """Fanart for a library details item, from its art map or the plain field."""
    return (detail.get('art', {}).get('fanart', '') or detail.get('fanart', '')).strip()


def refresh_pool_item(media_type: str, dbid: int) -> None:
    """Refresh one pool row from the item's current art, dropping it once the fanart is gone."""
    if media_type not in POOL_MEDIA_TYPES:
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
        plot = detail.get('description', '')
        year = None
    else:
        title = detail.get('title', '')
        plot = detail.get('plot', '')
        year = detail.get('year')

    artist = _joined_artist(detail.get('artist')) if media_type == 'musicvideo' else ''
    clearlogo = detail.get('art', {}).get('clearlogo', '')
    db_slideshow.upsert_pool_item(media_type, dbid, title, fanart, plot, year, artist, clearlogo)


def _video_items_with_fanart(method: str, result_key: str,
                             extra_properties: tuple = ()) -> Optional[list]:
    """Video library items carrying fanart; None means the fetch failed, [] means none have it."""
    response = request(method, {
        "properties": ["title", "art", "year", "plot", *extra_properties]
    })
    if response is None:
        return None
    return [item for item in response.get('result', {}).get(result_key, [])
            if item.get('art', {}).get('fanart', '').strip()]


def _get_movies_with_fanart() -> Optional[list]:
    """Movies with fanart, or None if the library fetch failed (vs [] = none have fanart)."""
    return _video_items_with_fanart("VideoLibrary.GetMovies", "movies")


def _get_tvshows_with_fanart() -> Optional[list]:
    """TV shows with fanart, or None if the library fetch failed (vs [] = none have fanart)."""
    return _video_items_with_fanart("VideoLibrary.GetTVShows", "tvshows")


def _get_artists_with_fanart() -> Optional[list]:
    """Artists with fanart, or None if the library fetch failed (vs [] = none have fanart)."""
    response = request("AudioLibrary.GetArtists", {
        "properties": ["fanart", "description", "art"]
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
                'description': artist.get('description', ''),
                'art': {'clearlogo': (artist.get('art') or {}).get('clearlogo', '')},
            })

    log("Service", f"Slideshow: Found {len(artists_with_fanart)} artists with fanart")
    return artists_with_fanart


def _get_musicvideos_with_fanart() -> Optional[list]:
    """Music videos with their own fanart, or None if the library fetch failed."""
    return _video_items_with_fanart(
        "VideoLibrary.GetMusicVideos", "musicvideos", ("artist",))


def is_pool_populated() -> bool:
    """Check if slideshow pool has any items."""
    return db_slideshow.is_pool_populated()
