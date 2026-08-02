"""Discovery widgets for trending, popular, and upcoming content."""
from __future__ import annotations

import traceback
from typing import Dict, List, Optional, Tuple

import xbmc
import xbmcgui
import xbmcplugin

from lib.kodi.client import ADDON, log, request, extract_result
from lib.data.api.utilities import tmdb_image_url

# Trakt wrapped responses nest the media object under "movie" or "show"
_TRAKT_WRAPPED = {
    "trakt_trending", "trakt_anticipated", "trakt_watched", "trakt_collected", "trakt_boxoffice",
}

WIDGET_REGISTRY: Dict[str, dict] = {
    "tmdb_trending":     {"provider": "tmdb", "types": ("movie", "tv"), "label": 32627},
    "tmdb_popular":      {"provider": "tmdb", "types": ("movie", "tv"), "label": 32628},
    "tmdb_top_rated":    {"provider": "tmdb", "types": ("movie", "tv"), "label": 32629},
    "tmdb_now_playing":  {"provider": "tmdb", "types": ("movie",), "label": 32630},
    "tmdb_upcoming":     {"provider": "tmdb", "types": ("movie",), "label": 32631},
    "tmdb_airing_today": {"provider": "tmdb", "types": ("tv",), "label": 32632},
    "tmdb_on_the_air":   {"provider": "tmdb", "types": ("tv",), "label": 32633},
    "trakt_trending":    {"provider": "trakt", "types": ("movie", "tv"), "label": 32634},
    "trakt_popular":     {"provider": "trakt", "types": ("movie", "tv"), "label": 32635},
    "trakt_anticipated": {"provider": "trakt", "types": ("movie", "tv"), "label": 32636},
    "trakt_watched":     {"provider": "trakt", "types": ("movie", "tv"), "label": 32637},
    "trakt_collected":   {"provider": "trakt", "types": ("movie", "tv"), "label": 32638},
    "trakt_boxoffice":   {"provider": "trakt", "types": ("movie",), "label": 32639},
    "trakt_recommendations": {
        "provider": "trakt", "types": ("movie", "tv"), "label": 32640, "auth": "oauth",
    },
}


def _get_library_lookup(media_type: str) -> Dict[str, Dict[str, object]]:
    """Map `tmdb_id -> {dbid, file}` for library `media_type` items, for "in library" matching."""
    lookup: Dict[str, Dict[str, object]] = {}

    if media_type == "movie":
        result = request("VideoLibrary.GetMovies", {
            "properties": ["uniqueid", "file"]
        })
        items = extract_result(result, 'movies', [])
        for item in items:
            tmdb_id = (item.get("uniqueid") or {}).get("tmdb")
            if tmdb_id:
                lookup[str(tmdb_id)] = {
                    "dbid": item["movieid"],
                    "file": item.get("file", "")
                }
    else:
        result = request("VideoLibrary.GetTVShows", {
            "properties": ["uniqueid"]
        })
        items = extract_result(result, 'tvshows', [])
        for item in items:
            tmdb_id = (item.get("uniqueid") or {}).get("tmdb")
            if tmdb_id:
                lookup[str(tmdb_id)] = {
                    "dbid": item["tvshowid"],
                    "file": f"videodb://tvshows/titles/{item['tvshowid']}/"
                }

    return lookup


def _normalize_tmdb_item(item: dict, media_type: str, genre_map: Dict[int, str]) -> dict:
    """Convert a raw TMDB response item into the normalized dict consumed by `_create_listitem`."""
    is_movie = media_type == "movie"
    genre_ids = item.get("genre_ids", [])
    genres = [genre_map[gid] for gid in genre_ids if gid in genre_map]

    date_field = "release_date" if is_movie else "first_air_date"
    premiered = item.get(date_field, "") or ""
    year = 0
    if premiered and len(premiered) >= 4:
        try:
            year = int(premiered[:4])
        except (ValueError, TypeError):
            pass
    poster = tmdb_image_url(item.get("poster_path"), 'w500')
    fanart = tmdb_image_url(item.get("backdrop_path"))

    return {
        "title": item.get("title") if is_movie else item.get("name", ""),
        "original_title": item.get("original_title") if is_movie else item.get("original_name", ""),
        "year": year,
        "overview": item.get("overview", ""),
        "rating": item.get("vote_average", 0.0),
        "votes": item.get("vote_count", 0),
        "genres": genres,
        "premiered": premiered,
        "poster": poster,
        "fanart": fanart,
        "tmdb_id": item.get("id"),
        "media_type": media_type,
    }


def _extract_trakt_media(item: dict, action: str, media_type: str) -> Optional[dict]:
    """Unwrap a Trakt item to its movie/show payload when the action wraps it, else return as-is."""
    if action in _TRAKT_WRAPPED:
        key = "movie" if media_type == "movie" else "show"
        return item.get(key)
    return item


def _trakt_image_url(paths: Optional[list]) -> str:
    """Pick the first Trakt image URL and prefix `https://`. Trakt URLs are protocol-less."""
    if not paths or not isinstance(paths, list):
        return ""
    raw = paths[0]
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    return f"https://{raw}"


def _normalize_trakt_item(media: dict, media_type: str) -> dict:
    """Convert a Trakt media object (`extended=full` images) to a normalized listitem dict."""
    is_movie = media_type == "movie"
    ids = media.get("ids", {})

    date_field = "released" if is_movie else "first_aired"
    premiered = (media.get(date_field) or "")[:10]
    year = media.get("year", 0) or 0

    genres_raw = media.get("genres", [])
    genres = [g.replace("-", " ").title() for g in genres_raw]
    images = media.get("images") or {}
    poster = _trakt_image_url(images.get("poster"))
    fanart = _trakt_image_url(images.get("fanart"))

    return {
        "title": media.get("title", ""),
        "original_title": media.get("title", ""),
        "year": year,
        "overview": media.get("overview", ""),
        "rating": media.get("rating", 0.0),
        "votes": media.get("votes", 0),
        "runtime": media.get("runtime", 0),
        "genres": genres,
        "certification": media.get("certification", ""),
        "premiered": premiered,
        "tagline": media.get("tagline", ""),
        "poster": poster,
        "fanart": fanart,
        "tmdb_id": ids.get("tmdb"),
        "imdb_id": ids.get("imdb", ""),
        "media_type": media_type,
    }


def _create_listitem(normalized: dict,
                     library_match: Optional[Dict[str, object]]
                     ) -> Tuple[str, xbmcgui.ListItem, bool]:
    """Build a `(url, ListItem, is_folder)` triple for one normalized discovery result."""
    title = normalized.get("title", "")
    listitem = xbmcgui.ListItem(title, offscreen=True)
    video_tag = listitem.getVideoInfoTag()

    is_movie = normalized["media_type"] == "movie"
    video_tag.setMediaType("movie" if is_movie else "tvshow")
    video_tag.setTitle(title)

    if normalized.get("original_title"):
        video_tag.setOriginalTitle(normalized["original_title"])
    if normalized.get("year"):
        video_tag.setYear(normalized["year"])
    if normalized.get("overview"):
        video_tag.setPlot(normalized["overview"])
    if normalized.get("rating"):
        video_tag.setRating(float(normalized["rating"]))
    if normalized.get("votes"):
        video_tag.setVotes(int(normalized["votes"]))
    if normalized.get("genres"):
        video_tag.setGenres(normalized["genres"])
    if normalized.get("premiered"):
        video_tag.setPremiered(normalized["premiered"])
    if normalized.get("certification"):
        video_tag.setMpaa(normalized["certification"])
    if normalized.get("tagline"):
        video_tag.setTagLine(normalized["tagline"])
    if normalized.get("runtime"):
        video_tag.setDuration(int(normalized["runtime"]) * 60)
    if normalized.get("imdb_id"):
        video_tag.setIMDBNumber(normalized["imdb_id"])

    art: Dict[str, str] = {}
    if normalized.get("poster"):
        art["poster"] = normalized["poster"]
    if normalized.get("fanart"):
        art["fanart"] = normalized["fanart"]
    if art:
        listitem.setArt(art)

    if normalized.get("tmdb_id"):
        listitem.setProperty("tmdb_id", str(normalized["tmdb_id"]))

    url = ""
    is_folder = not is_movie

    if library_match:
        dbid = int(library_match["dbid"])  # type: ignore[arg-type]
        video_tag.setDbId(dbid)
        listitem.setProperty("IsInLibrary", "true")
        url = str(library_match.get("file", ""))

    return url, listitem, is_folder


def _fetch_tmdb(action: str, media_type: str, page: int, window: str) -> list:
    """Dispatch a TMDB discovery action to its matching ApiTmdb call."""
    from lib.data.api.tmdb import ApiTmdb
    api = ApiTmdb()
    tmdb_type = "movie" if media_type == "movie" else "tv"

    dispatch = {
        "tmdb_trending": lambda: api.get_trending(tmdb_type, window=window, page=page),
        "tmdb_popular": lambda: api.get_popular(tmdb_type, page=page),
        "tmdb_top_rated": lambda: api.get_top_rated(tmdb_type, page=page),
        "tmdb_now_playing": lambda: api.get_now_playing(page=page),
        "tmdb_upcoming": lambda: api.get_upcoming(page=page),
        "tmdb_airing_today": lambda: api.get_airing_today(page=page),
        "tmdb_on_the_air": lambda: api.get_on_the_air(page=page),
    }
    return dispatch[action]()


def _fetch_trakt(action: str, media_type: str, limit: int, page: int, period: str) -> list:
    """Dispatch a Trakt discovery action to its matching ApiTrakt call."""
    from lib.data.api.trakt import ApiTrakt
    api = ApiTrakt()
    trakt_type = "movie" if media_type == "movie" else "show"

    dispatch = {
        "trakt_trending": lambda: api.get_trending(trakt_type, limit=limit, page=page),
        "trakt_popular": lambda: api.get_popular(trakt_type, limit=limit, page=page),
        "trakt_anticipated": lambda: api.get_anticipated(trakt_type, limit=limit, page=page),
        "trakt_watched": lambda: api.get_most_watched(
            trakt_type, period=period, limit=limit, page=page),
        "trakt_collected": lambda: api.get_most_collected(
            trakt_type, period=period, limit=limit, page=page),
        "trakt_boxoffice": lambda: api.get_box_office(limit=limit),
        "trakt_recommendations": lambda: api.get_recommendations(
            trakt_type, limit=limit, page=page),
    }
    return dispatch[action]()


_AUTH_WARN_PROP = "SkinInfo.Trakt.AuthWarned"
_AUTH_WARN_COOLDOWN = 10.0


def _warn_trakt_auth() -> None:
    """Notify that a Trakt-auth widget can't load; a short cooldown stops duplicate
    notifications from stacked widgets."""
    import time
    from lib.kodi.utilities import get_prop, set_prop
    last = get_prop(_AUTH_WARN_PROP)
    now = time.time()
    if last:
        try:
            if now - float(last) < _AUTH_WARN_COOLDOWN:
                return
        except ValueError:
            pass
    set_prop(_AUTH_WARN_PROP, str(now))
    from lib.infrastructure.dialogs import show_notification
    show_notification(
        ADDON.getLocalizedString(32612), ADDON.getLocalizedString(32613),
        xbmcgui.NOTIFICATION_WARNING, 4000,
    )


def handle_discover(handle: int, action: str, params: dict) -> None:
    """Plugin entry for a discovery widget: fetch, normalize, create ListItems, render directory."""
    try:
        config = WIDGET_REGISTRY.get(action)
        if not config:
            log("Plugin", f"Discover: Unknown widget '{action}'", xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

        if config.get("auth") == "oauth":
            from lib.data.api.trakt import ApiTrakt
            if not ApiTrakt().is_authorized():
                _warn_trakt_auth()
                xbmcplugin.endOfDirectory(handle, succeeded=True)
                return

        media_type = params.get("type", ["movie"])[0]
        valid_types = config["types"]
        if media_type not in valid_types:
            media_type = valid_types[0]

        source = params.get("source", ["online"])[0]
        limit = int(params.get("limit", ["20"])[0])
        page = int(params.get("page", ["1"])[0])
        window = params.get("window", ["week"])[0]
        period = params.get("period", ["weekly"])[0]

        kodi_media_type = "movie" if media_type == "movie" else "tvshow"
        library_lookup = _get_library_lookup(kodi_media_type)

        normalized_items: List[dict] = []

        if config["provider"] == "tmdb":
            from lib.data.api.tmdb import ApiTmdb
            tmdb_type = "movie" if media_type == "movie" else "tv"
            genre_map = ApiTmdb().get_genre_list(tmdb_type)
            raw_items = _fetch_tmdb(action, media_type, page, window)
            for raw in raw_items[:limit]:
                normalized_items.append(_normalize_tmdb_item(raw, media_type, genre_map))
        else:
            raw_items = _fetch_trakt(action, media_type, limit, page, period)
            medias = []
            for raw in raw_items:
                media_obj = _extract_trakt_media(raw, action, media_type)
                if media_obj:
                    medias.append(media_obj)

            for media_obj in medias:
                normalized_items.append(_normalize_trakt_item(media_obj, media_type))

        items: List[Tuple[str, xbmcgui.ListItem, bool]] = []
        for normalized in normalized_items:
            tmdb_id_str = str(normalized.get("tmdb_id", ""))
            lib_match = library_lookup.get(tmdb_id_str)

            if source == "library" and not lib_match:
                continue

            url, listitem, is_folder = _create_listitem(normalized, lib_match)
            items.append((url, listitem, is_folder))

        for url, listitem, is_folder in items:
            xbmcplugin.addDirectoryItem(handle, url, listitem, is_folder)

        content = "movies" if media_type == "movie" else "tvshows"
        xbmcplugin.setContent(handle, content)
        xbmcplugin.endOfDirectory(handle, succeeded=True)

        log("Plugin", f"Discover: {action} ({media_type}) returned {len(items)} items",
            xbmc.LOGINFO)

    except Exception as e:
        log("Plugin", f"Discover: Error - {e}", xbmc.LOGERROR)
        log("Plugin", traceback.format_exc(), xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(handle, succeeded=False)


def handle_tmdb_recommendations(handle: int, params: dict) -> None:
    """TMDB recommendations for a specific item; reads the cached `recommendations` block (no
    extra API call), resolving `tmdb_id` from `dbid`+`dbtype` if needed."""
    try:
        dbtype = params.get('dbtype', [''])[0]
        tmdb_id_str = params.get('tmdb_id', [''])[0]
        dbid_str = params.get('dbid', [''])[0]
        limit = int(params.get('limit', ['25'])[0])
        source = params.get('source', ['online'])[0]

        if dbtype not in ('movie', 'tvshow'):
            log("Plugin", f"TMDB Recommendations: Invalid dbtype '{dbtype}'", xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

        tmdb_id = 0
        if tmdb_id_str:
            try:
                tmdb_id = int(tmdb_id_str)
            except (ValueError, TypeError):
                tmdb_id = 0

        if not tmdb_id and dbid_str:
            from lib.data.api.person import resolve_tmdb_id
            try:
                dbid = int(dbid_str)
                resolved = resolve_tmdb_id(dbtype, dbid)
                tmdb_id = resolved or 0
            except (ValueError, TypeError):
                tmdb_id = 0

        if not tmdb_id:
            log("Plugin", "TMDB Recommendations: Could not resolve tmdb_id", xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

        from lib.data.api.tmdb import ApiTmdb
        api = ApiTmdb()
        data = api.get_complete_data(dbtype, tmdb_id)
        if not data:
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

        recs = (data.get('recommendations') or {}).get('results', [])[:limit]
        if not recs:
            xbmcplugin.endOfDirectory(handle, succeeded=True)
            return

        media_type = 'movie' if dbtype == 'movie' else 'tv'
        kodi_media_type = 'movie' if media_type == 'movie' else 'tvshow'
        tmdb_type = 'movie' if media_type == 'movie' else 'tv'

        library_lookup = _get_library_lookup(kodi_media_type)
        genre_map = api.get_genre_list(tmdb_type)

        items: List[Tuple[str, xbmcgui.ListItem, bool]] = []
        for raw in recs:
            normalized = _normalize_tmdb_item(raw, media_type, genre_map)
            tmdb_id_match = str(normalized.get("tmdb_id", ""))
            lib_match = library_lookup.get(tmdb_id_match)

            if source == "library" and not lib_match:
                continue

            url, listitem, is_folder = _create_listitem(normalized, lib_match)
            items.append((url, listitem, is_folder))

        for url, listitem, is_folder in items:
            xbmcplugin.addDirectoryItem(handle, url, listitem, is_folder)

        xbmcplugin.setContent(handle, "movies" if media_type == "movie" else "tvshows")
        xbmcplugin.endOfDirectory(handle, succeeded=True)

        log("Plugin",
            f"TMDB Recommendations: Returned {len(items)} items for {dbtype} tmdb={tmdb_id}",
            xbmc.LOGINFO)

    except Exception as e:
        log("Plugin", f"TMDB Recommendations: Error - {e}", xbmc.LOGERROR)
        log("Plugin", traceback.format_exc(), xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(handle, succeeded=False)


def _discover_url(action: str, media_type: str) -> str:
    """Build the discovery widget plugin:// URL for an action and media type."""
    return f"plugin://script.skin.info.service/?action={action}&type={media_type}"


def handle_discover_menu(handle: int, params: dict) -> None:
    """Render the top-level Discover menu (Movies / TV Shows)."""
    items = [
        (ADDON.getLocalizedString(32625),
         "plugin://script.skin.info.service/?action=discover_movies_menu", "DefaultMovies.png"),
        (ADDON.getLocalizedString(32626),
         "plugin://script.skin.info.service/?action=discover_tvshows_menu", "DefaultTVShows.png"),
    ]

    for label, path, icon in items:
        li = xbmcgui.ListItem(label, offscreen=True)
        li.setArt({"icon": icon, "thumb": icon})
        xbmcplugin.addDirectoryItem(handle, path, li, isFolder=True)

    xbmcplugin.endOfDirectory(handle, succeeded=True)


def handle_discover_movies_menu(handle: int, params: dict) -> None:
    """Render the movies sub-menu listing every movie-capable widget from WIDGET_REGISTRY."""
    for action, config in WIDGET_REGISTRY.items():
        if "movie" not in config["types"]:
            continue
        label = ADDON.getLocalizedString(config["label"])
        if config.get("auth") == "oauth":
            label += " " + ADDON.getLocalizedString(32641)
        li = xbmcgui.ListItem(label, offscreen=True)
        li.setArt({"icon": "DefaultMovies.png", "thumb": "DefaultMovies.png"})
        xbmcplugin.addDirectoryItem(handle, _discover_url(action, "movie"), li, isFolder=True)

    xbmcplugin.endOfDirectory(handle, succeeded=True)


def handle_discover_tvshows_menu(handle: int, params: dict) -> None:
    """Render the TV shows sub-menu listing every TV-capable widget from WIDGET_REGISTRY."""
    for action, config in WIDGET_REGISTRY.items():
        if "tv" not in config["types"]:
            continue
        label = ADDON.getLocalizedString(config["label"])
        if config.get("auth") == "oauth":
            label += " " + ADDON.getLocalizedString(32641)
        li = xbmcgui.ListItem(label, offscreen=True)
        li.setArt({"icon": "DefaultTVShows.png", "thumb": "DefaultTVShows.png"})
        xbmcplugin.addDirectoryItem(handle, _discover_url(action, "tv"), li, isFolder=True)

    xbmcplugin.endOfDirectory(handle, succeeded=True)
