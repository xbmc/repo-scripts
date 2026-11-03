"""Reads from Kodi's own video and music library, shared by the service and the plugin."""
from __future__ import annotations

from collections import OrderedDict
from typing import Dict, List, Optional, Tuple, Final

from lib.kodi.client import request, extract_result, get_item_details, decode_image_url
from lib.kodi.utilities import MULTI_VALUE_SEP, is_kodi_piers_or_later, join_multi


_ARTIST_PROPERTIES = [
    "description", "genre", "art", "thumbnail", "fanart", "musicbrainzartistid",
    "born", "formed", "died", "disbanded", "yearsactive", "instrument",
    "style", "mood", "type", "gender", "disambiguation", "sortname",
    "dateadded", "roles", "songgenres", "sourceid", "datemodified", "datenew",
    "compilationartist", "isalbumartist",
]

_ARTIST_ALBUM_PROPERTIES = [
    "title", "year", "artist", "artistid",
    "genre", "art", "albumlabel", "playcount", "rating",
]

_ALBUM_PROPERTIES = [
    "title", "art", "year", "artist", "artistid", "genre",
    "style", "mood", "type", "albumlabel", "playcount", "rating", "userrating",
    "musicbrainzalbumid", "musicbrainzreleasegroupid", "lastplayed", "dateadded",
    "description", "votes", "displayartist", "compilation", "releasetype",
    "sortartist", "songgenres", "totaldiscs", "releasedate", "originaldate", "albumduration",
]

_ALBUM_PROPERTIES_MIN = [
    "title", "art", "year", "artist", "genre", "albumlabel", "playcount", "rating",
]

_ALBUM_SONG_PROPERTIES = ["title", "duration", "track", "disc", "file", "art", "thumbnail"]


_artist_art_cache: "OrderedDict[str, Tuple[dict, object]]" = OrderedDict()
_artist_albums_cache: "OrderedDict[Tuple[str, str], str]" = OrderedDict()
_MAX_CACHE_ENTRIES: Final = 200


def _lru_set(cache: OrderedDict, key, value) -> None:
    """Set a key in an OrderedDict cache, evicting the oldest past `_MAX_CACHE_ENTRIES`."""
    cache[key] = value
    cache.move_to_end(key)
    if len(cache) > _MAX_CACHE_ENTRIES:
        cache.popitem(last=False)


def clear_musicvideo_library_art_cache() -> None:
    """Clear cached artist art lookups (call on library updates)."""
    _artist_art_cache.clear()
    _artist_albums_cache.clear()


def get_musicvideo_library_art(details: dict) -> dict:
    """Get `{Artist.Fanart, Artist.Thumb, Album.Thumb, ...}` matched from the music library."""
    artist_art, artist_id = get_musicvideo_artist_art(details)
    props = dict(artist_art)
    album_thumb = get_musicvideo_album_art(details, artist_id)
    if album_thumb:
        props["Album.Thumb"] = album_thumb
    return props


def get_musicvideo_artist_art(details: dict) -> tuple:
    """Get `(artist_props_dict, artist_id)` matched from AudioLibrary; cached per artist name."""

    artist_name = join_multi(details.get("artist"))
    if not artist_name:
        return {}, None

    artist_key = artist_name.lower()

    if artist_key in _artist_art_cache:
        _artist_art_cache.move_to_end(artist_key)
        artist_props, artist_id = _artist_art_cache[artist_key]
        return dict(artist_props), artist_id

    result = request("AudioLibrary.GetArtists", {
        "filter": {"field": "artist", "operator": "is", "value": artist_name},
        "properties": ["art"],
        "limits": {"end": 1},
    })

    artists_list = extract_result(result, 'artists')
    if not artists_list:
        _lru_set(_artist_art_cache, artist_key, ({}, None))
        return {}, None

    artist = artists_list[0]
    artist_art_raw = artist.get("art", {})
    artist_id = artist.get("artistid")

    artist_props: dict = {}
    for art_type in ("fanart", "thumb", "clearlogo", "banner"):
        value = artist_art_raw.get(art_type, "")
        if value:
            artist_props[f"Artist.{art_type.capitalize()}"] = decode_image_url(value)

    _lru_set(_artist_art_cache, artist_key, (artist_props, artist_id))
    return dict(artist_props), artist_id


def get_musicvideo_album_art(details: dict, artist_id: object) -> str:
    """Get the album thumb URL matched from AudioLibrary, or an empty string."""

    artist_name = join_multi(details.get("artist"))
    album_name = details.get("album") or ""
    if not album_name or not artist_id or not artist_name:
        return ""

    artist_key = artist_name.lower()
    album_cache_key = (artist_key, album_name.lower())

    if album_cache_key in _artist_albums_cache:
        _artist_albums_cache.move_to_end(album_cache_key)
        return _artist_albums_cache[album_cache_key]

    album_thumb = ""
    albums_result = request("AudioLibrary.GetAlbums", {
        "filter": {"artistid": artist_id},
        "properties": ["title", "art"],
    })
    if albums_result:
        album_list = extract_result(albums_result, 'albums')
        if isinstance(album_list, list):
            album_lower = album_name.lower()
            for album in album_list:
                if album.get("title", "").lower() == album_lower:
                    thumb = album.get("art", {}).get("thumb", "")
                    if thumb:
                        album_thumb = decode_image_url(thumb)
                    break
    _lru_set(_artist_albums_cache, album_cache_key, album_thumb)
    return album_thumb


def get_musicvideo_node_data(artist_name: str, album_name: str = "") -> dict:
    """Get music library art for musicvideo artist/album navigation nodes."""
    if not artist_name:
        return {}
    details: dict = {"artist": [artist_name], "album": album_name}
    return get_musicvideo_library_art(details)


def fetch_artist_details(artistid: int) -> Optional[Tuple[dict, List[dict]]]:
    """Fetch artist and their albums from library. Returns (artist, albums) or None."""
    artist = get_item_details(
        'artist',
        artistid,
        _ARTIST_PROPERTIES,
        cache_key=f"artist:{artistid}:details",
    )
    if not isinstance(artist, dict):
        return None

    albums_req = {
        "filter": {"artistid": artistid},
        "properties": _ARTIST_ALBUM_PROPERTIES,
        "sort": {"method": "year", "order": "ascending"},
    }
    albums_resp = request(
        "AudioLibrary.GetAlbums",
        albums_req,
        cache_key=f"artist:{artistid}:albums",
    )
    albums = extract_result(albums_resp, "albums") if albums_resp else []
    if not isinstance(albums, list):
        albums = []

    return artist, albums


def fetch_album_details(albumid: int) -> Optional[Tuple[dict, List[dict]]]:
    """Fetch album and its songs from library. Returns (album, songs) or None."""
    album = get_item_details(
        'album',
        albumid,
        _ALBUM_PROPERTIES,
        cache_key=f"album:{albumid}:details",
    )
    if not album:
        album = get_item_details(
            'album',
            albumid,
            _ALBUM_PROPERTIES_MIN,
            cache_key=f"album:{albumid}:details:min",
        )
    if not isinstance(album, dict):
        return None

    songs_req = {
        "filter": {"albumid": albumid},
        "properties": _ALBUM_SONG_PROPERTIES,
        "sort": {"method": "track", "order": "ascending"},
    }
    songs_resp = request(
        "AudioLibrary.GetSongs",
        songs_req,
        cache_key=f"album:{albumid}:songs",
    )
    songs = extract_result(songs_resp, "songs") if songs_resp else []
    if not isinstance(songs, list):
        songs = []

    return album, songs


def library_artist_mbid(artist_name: str) -> Optional[str]:
    """MusicBrainz ID for an artist from Kodi's music library, or None if not there."""
    primary_name = artist_name.split(MULTI_VALUE_SEP)[0].strip()
    if not primary_name:
        return None

    artists = extract_result(
        request("AudioLibrary.GetArtists", {
            "properties": ["musicbrainzartistid"],
            "filter": {"field": "artist", "operator": "is", "value": primary_name},
        }),
        "artists",
    )
    if not artists:
        return None

    mbid = artists[0].get("musicbrainzartistid")
    if isinstance(mbid, list):
        mbid = mbid[0] if mbid else None
    return mbid or None


def _get_episode_runtimes(tvshowid: int, season: Optional[int] = None) -> Tuple[List[int], int]:
    """Get the runtimes of a show's episodes that have one, and how many episodes there are."""
    props = ["runtime"] if is_kodi_piers_or_later() else ["runtime", "streamdetails"]
    params: Dict = {"tvshowid": tvshowid, "properties": props}
    if season is not None:
        params["season"] = season
    episodes = extract_result(request("VideoLibrary.GetEpisodes", params), "episodes")
    return [e["runtime"] for e in episodes if e.get("runtime", 0) > 0], len(episodes)


def resolve_show_runtime(tvshowid: int, episode_count: Optional[int] = None) -> Tuple[int, int]:
    """Resolve (total, average episode) runtime; a cached entry must match the episode count."""
    from lib.data.database import runtime as runtime_cache
    cached = runtime_cache.get_show_runtime(tvshowid, episode_count)
    if cached is not None:
        return cached
    runtimes, count = _get_episode_runtimes(tvshowid)
    total = sum(runtimes)
    avg = total // len(runtimes) if runtimes else 0
    runtime_cache.save_show_runtime(tvshowid, total, avg, count)
    return total, avg


def resolve_season_runtime(tvshowid: int, season: int, episode_count: Optional[int] = None) -> int:
    """Resolve a season's total runtime; a cached entry must match the episode count."""
    from lib.data.database import runtime as runtime_cache
    cached = runtime_cache.get_season_runtime(tvshowid, season, episode_count)
    if cached is not None:
        return cached
    runtimes, count = _get_episode_runtimes(tvshowid, season)
    total = sum(runtimes)
    runtime_cache.save_season_runtime(tvshowid, season, total, count)
    return total


_WATCH_MINUTES: Dict[int, Dict[Optional[int], int]] = {}
_WATCHED_EPISODES: Dict[int, Dict[int, int]] = {}
_watch_generation = 0


def cached_watch_minutes(tvshowid: int, season: Optional[int] = None) -> Optional[int]:
    """Cached minutes watched for a show, or one of its seasons; None when not fetched yet."""
    show = _WATCH_MINUTES.get(tvshowid)
    if show is None:
        return None
    return show.get(season, 0)


def cached_watched_episodes(tvshowid: int, season: int) -> Optional[int]:
    """Cached count of a season's watched episodes; None when the show is not fetched yet."""
    show = _WATCHED_EPISODES.get(tvshowid)
    if show is None:
        return None
    return show.get(season, 0)


def resolve_watch_minutes(tvshowid: int, season: Optional[int] = None) -> int:
    """Resolve the minutes watched for a show or season, one fetch covering all its seasons."""
    cached = cached_watch_minutes(tvshowid, season)
    if cached is not None:
        return cached
    generation = _watch_generation
    props = ["runtime", "playcount", "season"] if is_kodi_piers_or_later() else [
        "runtime", "playcount", "season", "streamdetails"]
    resp = request("VideoLibrary.GetEpisodes", {
        "tvshowid": tvshowid, "properties": props,
        "filter": {"field": "playcount", "operator": "greaterthan", "value": "0"},
    })
    if resp is None:
        return 0
    totals: Dict[Optional[int], int] = {None: 0}
    watched: Dict[int, int] = {}
    for episode in extract_result(resp, "episodes"):
        minutes = round((episode.get("runtime") or 0) / 60) * (episode.get("playcount") or 0)
        number = episode.get("season")
        totals[None] += minutes
        totals[number] = totals.get(number, 0) + minutes
        watched[number] = watched.get(number, 0) + 1
    if generation == _watch_generation:
        _WATCH_MINUTES[tvshowid] = totals
        _WATCHED_EPISODES[tvshowid] = watched
    return totals.get(season, 0)


def watch_minutes_cached() -> bool:
    """Whether any show's watch times are cached."""
    return bool(_WATCH_MINUTES)


def forget_watch_minutes(tvshowid: Optional[int] = None) -> None:
    """Forget one show's cached watch times, or every show's when the show is not known."""
    global _watch_generation
    _watch_generation += 1
    if tvshowid is None:
        _WATCH_MINUTES.clear()
        _WATCHED_EPISODES.clear()
    else:
        _WATCH_MINUTES.pop(tvshowid, None)
        _WATCHED_EPISODES.pop(tvshowid, None)
