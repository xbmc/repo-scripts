"""Get media details by DBID for plugin calls; queries the Kodi library and returns formatted
ListItem property dicts."""
from __future__ import annotations

import xbmc
import xbmcgui
import xbmcplugin
from collections import OrderedDict
from typing import List, Optional, Tuple
from lib.kodi.client import (
    request, extract_result, get_item_details, decode_image_url, KODI_MOVIE_PROPERTIES, log,
)
from lib.kodi.formatters import RATING_SOURCE_NORMALIZE
from lib.kodi.utilities import MULTI_VALUE_SEP
from lib.plugin.listitems import (
    build_movie_data,
    build_movieset_data,
    build_tvshow_data,
    build_season_data,
    build_episode_data,
    build_musicvideo_data,
    build_artist_data,
    build_album_data,
)
from lib.service.properties import join_multi


def split_multivalue(value: str, separator: str = MULTI_VALUE_SEP) -> list[str]:
    """Split multi-value string by separator, or return single-item list."""
    return value.split(separator) if separator in value else [value]


def _set_stream_details(video_tag: xbmc.InfoTagVideo, streamdetails: dict) -> None:
    """Add video/audio/subtitle streams from a JSON-RPC `streamdetails` dict to a `VideoInfoTag`."""
    video_streams = streamdetails.get("video") or []
    audio_streams = streamdetails.get("audio") or []
    subtitle_streams = streamdetails.get("subtitle") or []

    for v in video_streams:
        video_stream = xbmc.VideoStreamDetail(
            width=int(v.get("width") or 0),
            height=int(v.get("height") or 0),
            aspect=float(v.get("aspect") or 0.0),
            duration=int(v.get("duration") or 0),
            codec=v.get("codec") or "",
            stereomode="",
            language="",
            hdrtype=v.get("hdrtype") or "",
        )
        video_tag.addVideoStream(video_stream)

    for a in audio_streams:
        audio_stream = xbmc.AudioStreamDetail(
            channels=int(a.get("channels") or -1),
            codec=a.get("codec") or "",
            language=a.get("language") or "",
        )
        video_tag.addAudioStream(audio_stream)

    for s in subtitle_streams:
        subtitle_stream = xbmc.SubtitleStreamDetail(
            language=s.get("language") or "",
        )
        video_tag.addSubtitleStream(subtitle_stream)


_TVSHOW_PROPERTIES = [
    "title", "plot", "year", "premiered", "rating", "votes",
    "genre", "studio", "mpaa", "runtime", "episode", "season",
    "watchedepisodes", "imdbnumber", "originaltitle", "sorttitle",
    "episodeguide", "tag", "art", "userrating", "ratings",
    "cast", "uniqueid", "dateadded", "file", "lastplayed", "playcount",
    "trailer",
]

_SEASON_PROPERTIES = [
    "season", "showtitle", "playcount", "episode",
    "tvshowid", "watchedepisodes", "art", "userrating", "title",
]

_EPISODE_PROPERTIES = [
    "title", "plot", "rating", "votes", "ratings", "season", "episode",
    "showtitle", "firstaired", "runtime", "director", "writer", "file",
    "streamdetails", "art", "productioncode", "originaltitle", "playcount",
    "cast", "lastplayed", "resume", "tvshowid", "dateadded", "uniqueid",
    "userrating", "seasonid", "genre", "studio",
]

_MUSICVIDEO_PROPERTIES = [
    "title", "artist", "album", "genre", "year", "plot", "runtime",
    "director", "studio", "file", "streamdetails", "art", "premiered",
    "tag", "playcount",
    "lastplayed", "resume", "dateadded", "rating", "userrating", "uniqueid", "track",
]

_MOVIESET_PROPERTIES = ["title", "plot", "art"]

_MOVIESET_MOVIE_PROPERTIES = [
    "title", "year", "runtime", "genre", "director", "studio",
    "country", "writer", "plot", "plotoutline", "mpaa", "file",
    "streamdetails", "art", "thumbnail",
]

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


def get_item_data_by_dbid(media_type: str, dbid: int) -> Optional[dict]:
    """Query a library item by `(media_type, dbid)` and return ListItem property dict, or None."""
    handler = _MEDIA_TYPE_HANDLERS.get(media_type)
    if handler is None:
        log("Plugin", f"Unknown media type '{media_type}'", xbmc.LOGWARNING)
        return None
    try:
        return handler(dbid)
    except Exception as e:
        import traceback
        log("Plugin",
            f"Error getting data for {media_type} with DBID {dbid}: {str(e)}\n"
            f"{traceback.format_exc()}", xbmc.LOGERROR)
        return None


def _get_movie_data(movieid: int) -> Optional[dict]:
    """Get movie data as dictionary for ListItem."""
    details = get_item_details(
        'movie',
        movieid,
        KODI_MOVIE_PROPERTIES,
        cache_key=f"movie:{movieid}:details",
    )
    if not isinstance(details, dict):
        return None

    return build_movie_data(details)


def _get_movieset_data(setid: int) -> Optional[dict]:
    """Get movie set data as dictionary for ListItem."""
    details = get_item_details(
        'set',
        setid,
        _MOVIESET_PROPERTIES,
        cache_key=f"set:{setid}:details",
        ttl_seconds=300,
        movies={
            "properties": _MOVIESET_MOVIE_PROPERTIES,
            "sort": {"method": "year", "order": "ascending"},
        },
    )
    if not isinstance(details, dict):
        return None

    movies = details.get("movies") or []
    if not isinstance(movies, list):
        movies = []
    return build_movieset_data(details, movies)


def _get_tvshow_data(tvshowid: int) -> Optional[dict]:
    """Get TV show data as dictionary for ListItem."""
    details = get_item_details(
        'tvshow',
        tvshowid,
        _TVSHOW_PROPERTIES,
        cache_key=f"tvshow:{tvshowid}:details",
    )
    if not isinstance(details, dict):
        return None

    return build_tvshow_data(details)


def _get_season_data(seasonid: int) -> Optional[dict]:
    """Get season data as dictionary for ListItem."""
    details = get_item_details(
        'season',
        seasonid,
        _SEASON_PROPERTIES,
        cache_key=f"season:{seasonid}:details",
    )
    if not isinstance(details, dict):
        return None

    return build_season_data(details)


def _get_episode_data(episodeid: int) -> Optional[dict]:
    """Get episode data as dictionary for ListItem."""
    details = get_item_details(
        'episode',
        episodeid,
        _EPISODE_PROPERTIES,
        cache_key=f"episode:{episodeid}:details",
    )
    if not isinstance(details, dict):
        return None

    return build_episode_data(details)


def _get_musicvideo_data(musicvideoid: int) -> Optional[dict]:
    """Get music video data as dictionary for ListItem."""
    details = get_item_details(
        'musicvideo',
        musicvideoid,
        _MUSICVIDEO_PROPERTIES,
        cache_key=f"musicvideo:{musicvideoid}:details",
    )
    if not isinstance(details, dict):
        return None

    data = build_musicvideo_data(details)
    data.update(get_musicvideo_library_art(details))
    return data


_artist_art_cache: "OrderedDict[str, Tuple[dict, object]]" = OrderedDict()
_artist_albums_cache: "OrderedDict[Tuple[str, str], str]" = OrderedDict()
_MAX_CACHE_ENTRIES = 200


def _lru_set(cache: OrderedDict, key, value) -> None:
    """Insert into an OrderedDict cache with LRU eviction at `_MAX_CACHE_ENTRIES`."""
    cache[key] = value
    cache.move_to_end(key)
    if len(cache) > _MAX_CACHE_ENTRIES:
        cache.popitem(last=False)


def clear_musicvideo_library_art_cache() -> None:
    """Clear cached artist art lookups (call on library updates)."""
    _artist_art_cache.clear()
    _artist_albums_cache.clear()


def get_musicvideo_library_art(details: dict) -> dict:
    """Return `{Artist.Fanart, Artist.Thumb, Album.Thumb, ...}` matched from the music library."""
    artist_art, artist_id = get_musicvideo_artist_art(details)
    props = dict(artist_art)
    album_thumb = get_musicvideo_album_art(details, artist_id)
    if album_thumb:
        props["Album.Thumb"] = album_thumb
    return props


def get_musicvideo_artist_art(details: dict) -> tuple:
    """Return `(artist_props_dict, artist_id)` matched from AudioLibrary; caches per artist name."""

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
    """Return album thumb URL matched from AudioLibrary, or empty string."""

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


def _get_artist_data(artistid: int) -> Optional[dict]:
    """Get artist data as dictionary for ListItem."""
    result = fetch_artist_details(artistid)
    if not result:
        return None
    return build_artist_data(*result)


def _get_album_data(albumid: int) -> Optional[dict]:
    """Get album data as dictionary for ListItem."""
    result = fetch_album_details(albumid)
    if not result:
        return None
    return build_album_data(*result)


_MEDIA_TYPE_HANDLERS = {
    "movie":      _get_movie_data,
    "set":        _get_movieset_data,
    "tvshow":     _get_tvshow_data,
    "season":     _get_season_data,
    "episode":    _get_episode_data,
    "musicvideo": _get_musicvideo_data,
    "artist":     _get_artist_data,
    "album":      _get_album_data,
}


def handle_dbid_query(handle: int, params: dict) -> None:
    """Plugin entry `?action=getdetails&dbid=N&dbtype=X`: one ListItem with library properties."""
    dbid = params.get("dbid", [""])[0]
    media_type = params.get("dbtype", [""])[0]

    if not dbid:
        log("Plugin", "Missing required parameter 'dbid'", xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    try:
        dbid = int(dbid)
        if dbid <= 0:
            raise ValueError("DBID must be positive")
    except (ValueError, TypeError) as e:
        log("Plugin", f"Invalid DBID '{dbid}': {str(e)}", xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    if not media_type:
        log("Plugin", "Missing required parameter 'dbtype'", xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    media_type = media_type.lower().strip()

    if media_type in ("musicvideo_artist", "musicvideo_album"):
        from lib.plugin.online import handle_musicvideo_node
        handle_musicvideo_node(handle, params, media_type)
        return

    valid_types = (
        "movie", "tvshow", "season", "episode", "musicvideo", "artist", "album", "set"
    )

    if media_type not in valid_types:
        log("Plugin",
            f"Invalid media type '{media_type}', expected one of: {', '.join(valid_types)}",
            xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    log("Plugin", f"Querying {media_type} with DBID {dbid}", xbmc.LOGDEBUG)

    item_data = get_item_data_by_dbid(media_type, dbid)

    if not item_data:
        log("Plugin", f"No data returned for {media_type} {dbid}", xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    list_item = xbmcgui.ListItem(label=item_data.get("Title", ""), offscreen=True)

    is_music = media_type in ("artist", "album", "musicvideo")
    video_tag = list_item.getVideoInfoTag() if not is_music else None

    art_dict = {}
    properties_dict = {"DBID": str(dbid)}

    for key, value in item_data.items():
        if not value:
            continue

        if key.startswith("_"):
            continue

        if key.startswith("Art."):
            art_type = key.replace("Art.", "").lower()
            art_dict[art_type] = value
        else:
            properties_dict[key] = str(value)

    if video_tag:
        video_tag.setMediaType(media_type)
        video_tag.setDbId(dbid)

        if "_ratings" in item_data and isinstance(item_data["_ratings"], dict):
            ratings_dict = item_data["_ratings"]
            if ratings_dict:
                ratings_for_kodi = {}
                default_rating = None

                for rating_type, rating_info in ratings_dict.items():
                    if isinstance(rating_info, dict):
                        rating_val = rating_info.get("rating")
                        votes_val = rating_info.get("votes", 0)
                        max_val = rating_info.get("max", 10)
                        is_default = rating_info.get("default", False)

                        if rating_val is not None:
                            try:
                                ratings_for_kodi[rating_type] = (float(rating_val), int(votes_val))
                                if is_default:
                                    default_rating = rating_type

                                pct = max(0, min(100, round(
                                    (float(rating_val) / float(max_val)) * 100)))
                                output_type = RATING_SOURCE_NORMALIZE.get(rating_type, rating_type)
                                properties_dict[f"Rating.{output_type}.Percent"] = str(pct)
                            except (ValueError, TypeError, ZeroDivisionError):
                                pass

                if ratings_for_kodi:
                    video_tag.setRatings(ratings_for_kodi, default_rating or "")

        if "Title" in item_data:
            video_tag.setTitle(item_data["Title"])
        if "OriginalTitle" in item_data:
            video_tag.setOriginalTitle(item_data["OriginalTitle"])
        if "Year" in item_data:
            try:
                video_tag.setYear(int(item_data["Year"]))
            except (ValueError, TypeError):
                pass
        if "Rating" in item_data:
            try:
                video_tag.setRating(float(item_data["Rating"]))
            except (ValueError, TypeError):
                pass
        if "Votes" in item_data:
            try:
                votes_str = item_data["Votes"].replace(",", "")
                video_tag.setVotes(int(votes_str))
            except (ValueError, TypeError, AttributeError):
                pass
        if "UserRating" in item_data:
            try:
                video_tag.setUserRating(int(item_data["UserRating"]))
            except (ValueError, TypeError):
                pass
        if "Top250" in item_data:
            try:
                video_tag.setTop250(int(item_data["Top250"]))
            except (ValueError, TypeError):
                pass
        if "Playcount" in item_data:
            try:
                video_tag.setPlaycount(int(item_data["Playcount"]))
            except (ValueError, TypeError):
                pass
        if "Plot" in item_data:
            video_tag.setPlot(item_data["Plot"])
        if "PlotOutline" in item_data:
            video_tag.setPlotOutline(item_data["PlotOutline"])
        if "Tagline" in item_data:
            video_tag.setTagLine(item_data["Tagline"])
        if "Runtime" in item_data:
            try:
                video_tag.setDuration(int(item_data["Runtime"]) * 60)
            except (ValueError, TypeError):
                pass
        if "MPAA" in item_data:
            video_tag.setMpaa(item_data["MPAA"])
        if "Premiered" in item_data:
            video_tag.setPremiered(item_data["Premiered"])
        if "Genre" in item_data:
            video_tag.setGenres(split_multivalue(item_data["Genre"]))
        if "Director" in item_data:
            video_tag.setDirectors(split_multivalue(item_data["Director"]))
        if "Writer" in item_data:
            video_tag.setWriters(split_multivalue(item_data["Writer"]))
        if "Studio" in item_data:
            video_tag.setStudios(split_multivalue(item_data["Studio"]))
        if "Country" in item_data:
            video_tag.setCountries(split_multivalue(item_data["Country"]))
        if "Trailer" in item_data:
            video_tag.setTrailer(item_data["Trailer"])
        if "LastPlayed" in item_data:
            video_tag.setLastPlayed(item_data["LastPlayed"])
        if "DateAdded" in item_data:
            video_tag.setDateAdded(item_data["DateAdded"])
        if "Tag" in item_data:
            video_tag.setTags(split_multivalue(item_data["Tag"]))
        if "IMDBNumber" in item_data:
            video_tag.setIMDBNumber(item_data["IMDBNumber"])
        if "ProductionCode" in item_data:
            video_tag.setProductionCode(item_data["ProductionCode"])
        if "FirstAired" in item_data:
            video_tag.setFirstAired(item_data["FirstAired"])
        if "Episode" in item_data:
            try:
                video_tag.setEpisode(int(item_data["Episode"]))
            except (ValueError, TypeError):
                pass
        if "Season" in item_data:
            try:
                video_tag.setSeason(int(item_data["Season"]))
            except (ValueError, TypeError):
                pass
        if "ShowTitle" in item_data:
            video_tag.setTvShowTitle(item_data["ShowTitle"])

        if "_streamdetails" in item_data:
            _set_stream_details(video_tag, item_data["_streamdetails"])

    if art_dict:
        list_item.setArt(art_dict)

    if properties_dict:
        for prop_key, prop_value in properties_dict.items():
            list_item.setProperty(prop_key, prop_value)

    xbmcplugin.addDirectoryItem(handle, "", list_item, isFolder=False)
    xbmcplugin.endOfDirectory(handle, succeeded=True)
