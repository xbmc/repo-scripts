"""Plugin `getdetails` handler: a library item's details by DBID, as ListItem properties."""
from __future__ import annotations

import xbmc
import xbmcgui
import xbmcplugin
from typing import Optional
from lib.kodi.client import (
    get_item_details, KODI_MOVIE_PROPERTIES, log,
)
from lib.kodi.formatters import format_stars, RATING_SOURCE_NORMALIZE
from lib.kodi.utilities import MULTI_VALUE_SEP, parse_pipe_list, tvshow_version_fields
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
from lib.kodi.library import (
    cached_watched_episodes, fetch_album_details, fetch_artist_details,
    get_musicvideo_library_art, resolve_season_runtime, resolve_show_runtime,
    resolve_watch_minutes,
)


def _set_stream_details(video_tag: xbmc.InfoTagVideo, streamdetails: dict) -> None:
    """Set the video, audio and subtitle streams from a JSON-RPC stream details dict on a tag."""
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


def get_item_data_by_dbid(media_type: str, dbid: int) -> Optional[dict]:
    """Get a library item's ListItem property dict by media type and dbid, or None."""
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


def _with_raw_dates(data: dict, details: dict) -> dict:
    """Add the library's own last-played and date-added values for the info tag setters."""
    data["_lastplayed"] = details.get("lastplayed") or ""
    data["_dateadded"] = details.get("dateadded") or ""
    return data


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

    return _with_raw_dates(build_movie_data(details), details)


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
        _TVSHOW_PROPERTIES + tvshow_version_fields(),
        cache_key=f"tvshow:{tvshowid}:details",
    )
    if not isinstance(details, dict):
        return None

    total, avg = resolve_show_runtime(tvshowid, details.get("episode"))
    if not details.get("runtime") and avg:
        details["runtime"] = avg
    details["total_runtime"] = total
    if details.get("watchedepisodes"):
        details["watch_minutes"] = resolve_watch_minutes(tvshowid)

    return _with_raw_dates(build_tvshow_data(details), details)


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

    tvshowid = details.get("tvshowid")
    season = details.get("season")
    if tvshowid and tvshowid > 0 and season is not None:
        _, avg = resolve_show_runtime(tvshowid)
        if avg:
            details["runtime"] = avg
        details["total_runtime"] = resolve_season_runtime(tvshowid, season, details.get("episode"))
        details["watch_minutes"] = resolve_watch_minutes(tvshowid, season)
        # GetSeasonDetails never returns watchedepisodes
        details["watchedepisodes"] = cached_watched_episodes(tvshowid, season) or 0

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

    return _with_raw_dates(build_episode_data(details), details)


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
    return _with_raw_dates(data, details)


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
    media_type = params.get("dbtype", [""])[0].lower().strip()

    # music video artist and album nodes are looked up by name and carry no dbid
    if media_type in ("musicvideo_artist", "musicvideo_album"):
        from lib.plugin.online import handle_musicvideo_node
        handle_musicvideo_node(handle, params, media_type)
        return

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

    is_music = media_type in ("artist", "album")
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

                        if rating_val:
                            try:
                                ratings_for_kodi[rating_type] = (float(rating_val), int(votes_val))
                                if is_default:
                                    default_rating = rating_type

                                pct = max(0, min(100, round(
                                    (float(rating_val) / float(max_val)) * 100)))
                                output_type = RATING_SOURCE_NORMALIZE.get(rating_type, rating_type)
                                properties_dict[f"Rating.{output_type}.Percent"] = str(pct)
                                stars = format_stars(
                                    output_type, float(rating_val) / float(max_val) * 10.0)
                                if stars:
                                    properties_dict[f"Rating.{output_type}.Stars"] = stars
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
            video_tag.setGenres(parse_pipe_list(item_data["Genre"], MULTI_VALUE_SEP))
        if "Director" in item_data:
            video_tag.setDirectors(parse_pipe_list(item_data["Director"], MULTI_VALUE_SEP))
        if "Writer" in item_data:
            video_tag.setWriters(parse_pipe_list(item_data["Writer"], MULTI_VALUE_SEP))
        if "Studio" in item_data:
            video_tag.setStudios(parse_pipe_list(item_data["Studio"], MULTI_VALUE_SEP))
        if "Country" in item_data:
            video_tag.setCountries(parse_pipe_list(item_data["Country"], MULTI_VALUE_SEP))
        if "Trailer" in item_data:
            video_tag.setTrailer(item_data["Trailer"])
        if item_data.get("_lastplayed"):
            video_tag.setLastPlayed(item_data["_lastplayed"])
        if item_data.get("_dateadded"):
            video_tag.setDateAdded(item_data["_dateadded"])
        if "Tag" in item_data:
            video_tag.setTags(parse_pipe_list(item_data["Tag"], MULTI_VALUE_SEP))
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
