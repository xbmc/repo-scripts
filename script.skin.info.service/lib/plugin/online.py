"""Online-data plugin handlers for library items, music videos and music video nodes."""
from __future__ import annotations

import xbmc
import xbmcgui
import xbmcplugin

from lib.kodi.client import log


def handle_online(handle: int, params: dict) -> None:
    """Plugin entry for the online-data ListItem, by `dbid`+`dbtype` or by `tmdb_id`/`imdb_id`."""
    from lib.data.online import fetch_all_online_data, show_scoped_props
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
    episode_details: dict = {}

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
            episode_details = get_item_details(
                "episode", dbid_int, ["tvshowid", "season", "episode", "uniqueid"]) or {}
            if not episode_details.get("tvshowid"):
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

    # an episode's online data is its show's, ratings aside
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

    if is_episode:
        online_data = show_scoped_props(online_data)
        if episode_details:
            from lib.service.online.fetchers import fetch_episode_ratings
            online_data.update(fetch_episode_ratings(
                imdb_id, tmdb_id, episode_details["season"], episode_details["episode"],
                (episode_details.get("uniqueid") or {}).get("imdb") or ""))

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
    from lib.data.music import (
        fetch_artist_online_data,
        fetch_track_online_data,
        fetch_album_online_data,
        extract_track_properties,
        extract_album_properties,
    )
    from lib.kodi.utilities import join_multi

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
    from lib.kodi.library import get_musicvideo_node_data

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
