"""Fetchers for OMDb, MDBList, and Trakt data used by `service.online.fetch_all_online_data`,
plus plugin handlers for online-data display, musicvideo nodes, and TMDB details."""
from __future__ import annotations

from typing import Dict, Optional

import xbmc
import xbmcgui
import xbmcplugin

from lib.kodi.client import log
from lib.kodi.formatters import (
    format_rating_props,
    build_common_sense_summary,
    RATING_SOURCE_NORMALIZE,
)
from lib.kodi.utilities import MULTI_VALUE_SEP


def fetch_omdb_data(media_type: str, imdb_id: str, abort_flag=None) -> Dict[str, str]:
    """Fetch OMDb awards plus ratings (imdb/metacritic/rotten tomatoes) from the same response."""
    from lib.data.api.omdb import ApiOmdb

    props: Dict[str, str] = {}

    if not imdb_id:
        return props

    if abort_flag and abort_flag.is_requested():
        return props

    try:
        omdb = ApiOmdb()
        awards_data = omdb.get_awards(imdb_id, abort_flag=abort_flag)
        if awards_data:
            props["Awards.Oscar.Wins"] = str(awards_data.get("oscar_wins", 0))
            props["Awards.Oscar.Nominations"] = str(awards_data.get("oscar_nominations", 0))
            props["Awards.Emmy.Wins"] = str(awards_data.get("emmy_wins", 0))
            props["Awards.Emmy.Nominations"] = str(awards_data.get("emmy_nominations", 0))
            props["Awards.Other.Wins"] = str(awards_data.get("other_wins", 0))
            props["Awards.Other.Nominations"] = str(awards_data.get("other_nominations", 0))
            props["Awards"] = awards_data.get("awards_text", "")

        ratings = omdb.fetch_ratings(media_type, {"imdb": imdb_id}, abort_flag=abort_flag)
        if ratings:
            for source, info in ratings.items():
                if isinstance(info, dict) and "rating" in info and "votes" in info:
                    props.update(format_rating_props(source, info["rating"], int(info["votes"])))
    except Exception as e:
        log("Plugin", f"OMDb fetch error: {e}", xbmc.LOGWARNING)

    return props


def fetch_mdblist_data(
    media_type: str,
    imdb_id: str,
    tmdb_id: str,
    is_episode: bool,
    abort_flag=None
) -> Dict[str, str]:
    """Fetch MDBList data (extra info, common sense, ratings)."""
    from lib.data.api.mdblist import ApiMdblist

    props: Dict[str, str] = {}

    if not imdb_id and not tmdb_id:
        return props

    if abort_flag and abort_flag.is_requested():
        return props

    mdblist_media_type = "tvshow" if is_episode else media_type

    try:
        mdblist = ApiMdblist()
        ids = {"imdb": imdb_id, "tmdb": tmdb_id}

        extra_data = mdblist.get_extra_data(mdblist_media_type, ids, abort_flag=abort_flag)
        if abort_flag and abort_flag.is_requested():
            return props
        if extra_data:
            if "trailer" in extra_data:
                props["MDBList.Trailer"] = extra_data["trailer"]
            if "certification" in extra_data:
                props["MDBList.Certification"] = extra_data["certification"]

        cs_data = mdblist.get_common_sense_data(mdblist_media_type, ids, abort_flag=abort_flag)
        if abort_flag and abort_flag.is_requested():
            return props
        if cs_data:
            props["CommonSense.Age"] = str(cs_data["age"])
            props["CommonSense.Violence"] = str(cs_data["violence"])
            props["CommonSense.Nudity"] = str(cs_data["nudity"])
            props["CommonSense.Language"] = str(cs_data["language"])
            props["CommonSense.Drinking"] = str(cs_data["drinking"])
            props["CommonSense.Selection"] = "true" if cs_data["selection"] else "false"

            summary, reasons = build_common_sense_summary(cs_data)
            if summary:
                props["CommonSense.Summary"] = summary
                props["CommonSense.Reasons"] = reasons

        service_ratings = mdblist.get_service_ratings(
            mdblist_media_type, ids, abort_flag=abort_flag
        )
        if abort_flag and abort_flag.is_requested():
            return props
        if service_ratings:
            for source, rating_data in service_ratings.items():
                if (
                    isinstance(rating_data, dict)
                    and "rating" in rating_data and "votes" in rating_data
                ):
                    normalized_source = RATING_SOURCE_NORMALIZE.get(source, source)
                    props.update(format_rating_props(
                        normalized_source, rating_data["rating"], int(rating_data["votes"])
                    ))

        rt_status = mdblist.get_rt_status(mdblist_media_type, ids, abort_flag=abort_flag)
        if rt_status:
            if rt_status.get("certified"):
                props["Tomatometer"] = "Certified"
            elif rt_status.get("fresh"):
                props["Tomatometer"] = "Fresh"
            elif rt_status.get("rotten"):
                props["Tomatometer"] = "Rotten"

            if rt_status.get("hot"):
                props["Popcornmeter"] = "Hot"
            elif rt_status.get("popcorn"):
                props["Popcornmeter"] = "Fresh"
            elif rt_status.get("stale"):
                props["Popcornmeter"] = "Spilled"

    except Exception as e:
        log("Plugin", f"MDBList fetch error: {e}", xbmc.LOGWARNING)

    return props


def fetch_trakt_data(
    media_type: str,
    imdb_id: str,
    tmdb_id: str,
    is_episode: bool,
    season: Optional[int],
    episode: Optional[int],
    abort_flag=None
) -> Dict[str, str]:
    """Fetch Trakt ratings and subgenres."""
    from lib.data.api.trakt import ApiTrakt

    props: Dict[str, str] = {}

    if not imdb_id and not tmdb_id:
        return props

    if abort_flag and abort_flag.is_requested():
        return props

    try:
        trakt = ApiTrakt()
        trakt_ids: Dict[str, str] = {"imdb": imdb_id or "", "tmdb": tmdb_id or ""}
        if is_episode and season is not None and episode is not None:
            trakt_ids["season"] = str(season)
            trakt_ids["episode"] = str(episode)

        trakt_ratings = trakt.fetch_ratings(media_type, trakt_ids, abort_flag=abort_flag)
        if abort_flag and abort_flag.is_requested():
            return props
        if trakt_ratings and "trakt" in trakt_ratings:
            trakt_data = trakt_ratings["trakt"]
            props.update(format_rating_props(
                "trakt", trakt_data["rating"], int(trakt_data["votes"])
            ))

        if not is_episode:
            trakt_id = imdb_id or tmdb_id
            subgenres = trakt.get_subgenres(trakt_id, media_type, abort_flag=abort_flag)
            if subgenres:
                props["Trakt.Subgenres"] = MULTI_VALUE_SEP.join(subgenres)
    except Exception as e:
        log("Plugin", f"Trakt fetch error: {e}", xbmc.LOGWARNING)

    return props


def handle_online(handle: int, params: dict) -> None:
    """Plugin entry for the online-data ListItem; library mode needs `dbid`+`dbtype`, direct mode
    needs `tmdb_id` or `imdb_id`."""
    from lib.service.online import fetch_all_online_data
    from lib.kodi.client import get_item_details
    from lib.data.api.tmdb import ApiTmdb

    media_type = params.get("dbtype", [""])[0]
    dbid = params.get("dbid", [""])[0]
    tmdb_id = params.get("tmdb_id", [""])[0]
    imdb_id = params.get("imdb_id", [""])[0]

    if not media_type:
        log("Plugin", "Online: Missing required parameter 'dbtype'", xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    media_type = media_type.lower().strip()

    if media_type == "musicvideo":
        _handle_online_musicvideo(handle, params)
        return

    valid_types = ("movie", "tvshow", "episode")

    if media_type not in valid_types:
        log(
            "Plugin",
            f"Online: Invalid media type '{media_type}', expected one of: "
            f"{', '.join(valid_types)}",
            xbmc.LOGWARNING,
        )
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    is_episode = media_type == "episode"
    tvdb_id = ""

    if tmdb_id or imdb_id:
        log("Plugin", f"Online: Direct mode - TMDB: {tmdb_id}, IMDB: {imdb_id}", xbmc.LOGDEBUG)
    elif dbid:
        try:
            dbid_int = int(dbid)
            if dbid_int <= 0:
                raise ValueError("DBID must be positive")
        except (ValueError, TypeError) as e:
            log("Plugin", f"Online: Invalid DBID '{dbid}': {str(e)}", xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

        log("Plugin", f"Online: Library mode - {media_type} DBID {dbid}", xbmc.LOGDEBUG)

        if is_episode:
            episode_details = get_item_details("episode", dbid_int, ["tvshowid"])
            if not episode_details or not episode_details.get("tvshowid"):
                log(
                    "Plugin",
                    f"Online: Could not get parent show for episode {dbid}",
                    xbmc.LOGWARNING,
                )
                xbmcplugin.endOfDirectory(handle, succeeded=False)
                return
            tvshow_dbid = episode_details["tvshowid"]
            details = get_item_details("tvshow", tvshow_dbid, ["uniqueid"])
        else:
            details = get_item_details(media_type, dbid_int, ["uniqueid"])

        if not details:
            log("Plugin", f"Online: Could not get details for {media_type} {dbid}", xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

        uniqueid_dict = details.get("uniqueid") or {}
        imdb_id = uniqueid_dict.get("imdb") or ""
        tmdb_id = uniqueid_dict.get("tmdb") or ""
        tvdb_id = uniqueid_dict.get("tvdb") or ""
    else:
        log(
            "Plugin",
            "Online: Missing required parameter - provide dbid, tmdb_id, or imdb_id",
            xbmc.LOGWARNING,
        )
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    # Episodes use parent show's data for online lookups
    if is_episode:
        media_type = "tvshow"

    if not imdb_id and not tmdb_id and not tvdb_id:
        log("Plugin", "Online: No valid IDs available", xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    if not tmdb_id:
        tmdb_api = ApiTmdb()
        if imdb_id:
            result = tmdb_api.find_by_external_id(imdb_id, "imdb_id", media_type)
            if result and result.get("id"):
                tmdb_id = str(result["id"])
        elif tvdb_id and media_type == "tvshow":
            result = tmdb_api.find_by_external_id(tvdb_id, "tvdb_id", media_type)
            if result and result.get("id"):
                tmdb_id = str(result["id"])

    log("Plugin", f"Online: Resolved IDs - IMDB: {imdb_id}, TMDB: {tmdb_id}", xbmc.LOGDEBUG)

    is_library_item = bool(dbid)
    online_data = fetch_all_online_data(
        media_type, imdb_id, tmdb_id, is_library_item=is_library_item
    )

    if not online_data:
        xbmcplugin.endOfDirectory(handle, succeeded=True)
        return

    list_item = xbmcgui.ListItem(offscreen=True)

    if dbid:
        list_item.setProperty("dbid", str(dbid))

    for prop_key, prop_value in online_data.items():
        if prop_value:
            list_item.setProperty(prop_key, str(prop_value))

    xbmcplugin.addDirectoryItem(handle, "", list_item, isFolder=False)
    xbmcplugin.endOfDirectory(handle, succeeded=True)


def _handle_online_musicvideo(handle: int, params: dict) -> None:
    """Fetch online music metadata for a music video and return as ListItem properties."""
    from lib.kodi.client import get_item_details
    from lib.service.music import (
        fetch_artist_online_data,
        fetch_track_online_data,
        fetch_album_online_data,
        extract_track_properties,
        extract_album_properties,
    )
    from lib.service.properties import join_multi

    dbid = params.get("dbid", [""])[0]
    if not dbid:
        log("Plugin", "Online MusicVideo: Missing required parameter 'dbid'", xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    try:
        dbid_int = int(dbid)
        if dbid_int <= 0:
            raise ValueError("DBID must be positive")
    except (ValueError, TypeError) as e:
        log("Plugin", f"Online MusicVideo: Invalid DBID '{dbid}': {e}", xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    details = get_item_details("musicvideo", dbid_int, ["artist", "title", "album"])
    if not details:
        log("Plugin", f"Online MusicVideo: No details for DBID {dbid}", xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    artist_name = join_multi(details.get("artist"))
    title = details.get("title") or None
    album = details.get("album") or None

    props: dict[str, str] = {}

    if artist_name:
        result = fetch_artist_online_data(artist_name, album=album, track=title)
        if result:
            if result.bio:
                props["Artist.Bio"] = result.bio
            props["Artist.FanArt.Count"] = str(len(result.fanart_urls))
            if result.fanart_urls:
                props["Artist.FanArt"] = result.fanart_urls[0]
            for art_type in ("thumb", "clearlogo", "banner"):
                url = result.artist_art.get(art_type, "")
                if url:
                    key = art_type[0].upper() + art_type[1:]
                    props[f"Artist.{key}"] = url

    if artist_name and title:
        fetch_track_online_data(artist_name, title)
        track_props = extract_track_properties(artist_name, title)
        if track_props:
            for k, v in track_props.items():
                props[f"Track.{k}"] = v

    if artist_name and album:
        fetch_album_online_data(artist_name, album)
        album_props = extract_album_properties(artist_name, album)
        if album_props:
            for k, v in album_props.items():
                props[f"Album.{k}"] = v

    if not props:
        xbmcplugin.endOfDirectory(handle, succeeded=True)
        return

    list_item = xbmcgui.ListItem(offscreen=True)
    list_item.setProperty("dbid", str(dbid))

    for prop_key, prop_value in props.items():
        if prop_value:
            list_item.setProperty(prop_key, str(prop_value))

    xbmcplugin.addDirectoryItem(handle, "", list_item, isFolder=False)
    xbmcplugin.endOfDirectory(handle, succeeded=True)


def handle_musicvideo_node(handle: int, params: dict, media_type: str) -> None:
    """Handle musicvideo artist/album node queries using name-based library lookup."""
    from lib.plugin.dbid import get_musicvideo_node_data

    artist_name = params.get("artist", [""])[0]
    album_name = params.get("album", [""])[0]

    if media_type == "musicvideo_artist" and not artist_name:
        log("Plugin", "MusicVideo node: Missing 'artist' parameter", xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    if media_type == "musicvideo_album" and not album_name:
        log("Plugin", "MusicVideo node: Missing 'album' parameter", xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    data = get_musicvideo_node_data(artist_name, album_name)

    label = artist_name if media_type == "musicvideo_artist" else album_name
    list_item = xbmcgui.ListItem(label=label, offscreen=True)

    for prop_key, prop_value in data.items():
        if prop_value:
            list_item.setProperty(prop_key, str(prop_value))

    xbmcplugin.addDirectoryItem(handle, "", list_item, isFolder=False)
    xbmcplugin.endOfDirectory(handle, succeeded=True)
