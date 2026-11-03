"""Discovery widgets for trending, popular, and upcoming content."""
from __future__ import annotations

import sys
from typing import Dict, Iterable, List, Optional, Tuple, Final

import xbmc
import xbmcgui
import xbmcplugin

from lib.kodi.client import ADDON, log, get_item_details
from lib.data.api.utilities import tmdb_image_url, trakt_image_url

# Trakt wrapped responses nest the media object under "movie" or "show"
_TRAKT_WRAPPED = {
    "trakt_trending", "trakt_anticipated", "trakt_watched", "trakt_collected", "trakt_boxoffice",
    "trakt_played", "trakt_watchlist", "trakt_history", "trakt_inprogress",
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
    "trakt_played":      {"provider": "trakt", "types": ("movie", "tv"), "label": 32125},
    "trakt_watchlist": {
        "provider": "trakt", "types": ("movie", "tv"), "label": 32084, "auth": "oauth",
    },
    "trakt_history": {
        "provider": "trakt", "types": ("movie", "tv"), "label": 32123, "auth": "oauth",
    },
    "trakt_inprogress": {"provider": "trakt", "types": ("tv",), "label": 32124, "auth": "oauth"},
}

# show history lists episodes, several per show
_HISTORY_EPISODES_PER_SHOW = 5


def _get_library_lookup(media_type: str, tmdb_ids: Iterable) -> Dict[str, Dict[str, object]]:
    """Map `tmdb_id -> {dbid, file}` for the ids that are in the library."""
    from lib.data.database.rollcall import get_dbids_by_tmdb

    lookup: Dict[str, Dict[str, object]] = {}
    for tmdb_id, dbid in get_dbids_by_tmdb(media_type, tmdb_ids).items():
        if media_type == "movie":
            details = get_item_details("movie", dbid, ["file"])
            file_path = (details or {}).get("file", "")
            if not file_path:
                continue
        else:
            file_path = f"videodb://tvshows/titles/{dbid}/"
        lookup[tmdb_id] = {"dbid": dbid, "file": file_path}

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
    poster = trakt_image_url(images.get("poster"))
    fanart = trakt_image_url(images.get("fanart"))

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
        listitem.setProperty("isinlibrary", "true")
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
        "trakt_played": lambda: api.get_most_played(
            trakt_type, period=period, limit=limit, page=page),
        "trakt_watchlist": lambda: api.get_watchlist(trakt_type, limit=limit, page=page),
        "trakt_history": lambda: api.get_history(
            trakt_type, page=page,
            limit=limit if trakt_type == "movie" else limit * _HISTORY_EPISODES_PER_SHOW),
        "trakt_inprogress": lambda: api.get_up_next(limit=limit, page=page),
    }
    return dispatch[action]()


_AUTH_WARN_PROP: Final = "SkinInfo.Trakt.AuthWarned"
_AUTH_WARN_COOLDOWN: Final = 10.0


def warn_trakt_auth() -> None:
    """Warn that a Trakt widget needs an account, at most once per cooldown across widgets."""
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
    """Plugin entry for a TMDB or Trakt discovery widget, flagging titles already in the library."""
    try:
        config = WIDGET_REGISTRY.get(action)
        if not config:
            log("Plugin", f"Discover: Unknown widget '{action}'", xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

        xbmcplugin.setPluginCategory(handle, ADDON.getLocalizedString(config["label"]))
        if config.get("auth") == "oauth":
            from lib.data.api.trakt import ApiTrakt
            if not ApiTrakt().is_authorized():
                warn_trakt_auth()
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

            seen = set()
            for media_obj in medias:
                normalized = _normalize_trakt_item(media_obj, media_type)
                key = normalized.get("tmdb_id") or normalized.get("title")
                if key not in seen:
                    seen.add(key)
                    normalized_items.append(normalized)
            normalized_items = normalized_items[:limit]

        library_lookup = _get_library_lookup(
            kodi_media_type, [n.get("tmdb_id") for n in normalized_items]
        )

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
            xbmc.LOGDEBUG)

    except Exception as e:
        import traceback
        log("Plugin", f"Discover: Error - {e}", xbmc.LOGERROR)
        log("Plugin", traceback.format_exc(), xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(handle, succeeded=False)


_TRAKT_LIST_KINDS: Final = ("mine", "liked", "popular", "trending")


def handle_trakt_lists(handle: int, params: dict) -> None:
    """Plugin entry for Trakt lists as folders: the account's own or liked, popular or trending."""
    try:
        kind = params.get("kind", ["popular"])[0]
        if kind not in _TRAKT_LIST_KINDS:
            kind = "popular"
        limit = int(params.get("limit", ["20"])[0])
        page = int(params.get("page", ["1"])[0])

        from lib.data.api.trakt import ApiTrakt
        api = ApiTrakt()
        if kind in ("mine", "liked") and not api.is_authorized():
            warn_trakt_auth()
            xbmcplugin.endOfDirectory(handle, succeeded=True)
            return

        from urllib.parse import urlencode
        for entry in api.get_lists(kind, limit=limit, page=page):
            list_id = (entry.get("ids") or {}).get("trakt")
            owner = entry.get("user") or {}
            user = "me" if kind == "mine" else (owner.get("ids") or {}).get("slug", "")
            if not list_id or not user:
                continue
            count = str(entry.get("item_count") or "")
            item = xbmcgui.ListItem(entry.get("name", ""), count, offscreen=True)
            item.getVideoInfoTag().setPlot(entry.get("description") or "")
            poster = trakt_image_url((entry.get("images") or {}).get("posters"))
            if poster:
                item.setArt({"poster": poster, "thumb": poster})
            props = {
                "user": owner.get("name") or owner.get("username") or "",
                "item_count": count,
                "likes": str(entry.get("likes") or ""),
            }
            for key, value in props.items():
                if value:
                    item.setProperty(key, value)
            query = urlencode({"action": "trakt_list_items", "user": user, "list": list_id})
            xbmcplugin.addDirectoryItem(
                handle, f"plugin://script.skin.info.service/?{query}", item, True)

        xbmcplugin.setContent(handle, "videos")
        xbmcplugin.endOfDirectory(handle, succeeded=True)

    except Exception as e:
        import traceback
        log("Plugin", f"Trakt Lists: Error - {e}", xbmc.LOGERROR)
        log("Plugin", traceback.format_exc(), xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(handle, succeeded=False)


def handle_trakt_list_items(handle: int, params: dict) -> None:
    """Plugin entry for the movies and shows on one Trakt list, in its rank order."""
    try:
        user = params.get("user", [""])[0]
        list_id = params.get("list", [""])[0]
        if not user or not list_id:
            log("Plugin", "Trakt List Items: Missing user or list", xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return
        media_type = params.get("type", [""])[0]
        source = params.get("source", ["online"])[0]
        limit = int(params.get("limit", ["20"])[0])
        page = int(params.get("page", ["1"])[0])

        from lib.data.api.trakt import ApiTrakt
        api = ApiTrakt()
        if user == "me" and not api.is_authorized():
            warn_trakt_auth()
            xbmcplugin.endOfDirectory(handle, succeeded=True)
            return

        normalized = []
        for entry in api.get_list_items(user, list_id, media_type, limit=limit, page=page):
            kind = entry.get("type")
            media = entry.get(kind) if kind in ("movie", "show") else None
            if isinstance(media, dict):
                normalized.append(
                    _normalize_trakt_item(media, "movie" if kind == "movie" else "tv"))

        lookups: Dict[str, Dict[str, Dict[str, object]]] = {}
        for item_type, kodi_type in (("movie", "movie"), ("tv", "tvshow")):
            tmdb_ids = [n["tmdb_id"] for n in normalized
                        if n["media_type"] == item_type and n.get("tmdb_id")]
            lookups[item_type] = _get_library_lookup(kodi_type, tmdb_ids) if tmdb_ids else {}

        for normalized_item in normalized:
            lib_match = lookups[normalized_item["media_type"]].get(
                str(normalized_item.get("tmdb_id", "")))
            if source == "library" and not lib_match:
                continue
            url, listitem, is_folder = _create_listitem(normalized_item, lib_match)
            xbmcplugin.addDirectoryItem(handle, url, listitem, is_folder)

        item_types = {n["media_type"] for n in normalized}
        content = {frozenset({"movie"}): "movies", frozenset({"tv"}): "tvshows"}.get(
            frozenset(item_types), "videos")
        xbmcplugin.setContent(handle, content)
        xbmcplugin.endOfDirectory(handle, succeeded=True)

    except Exception as e:
        import traceback
        log("Plugin", f"Trakt List Items: Error - {e}", xbmc.LOGERROR)
        log("Plugin", traceback.format_exc(), xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(handle, succeeded=False)


def _seed_tmdb_id(dbtype: str, params: dict) -> int:
    """TMDB id of the item a list is seeded by, from `tmdb_id` or a library `dbid`; 0 if unknown."""
    tmdb_id_str = params.get('tmdb_id', [''])[0]
    if tmdb_id_str.isdigit():
        return int(tmdb_id_str)
    dbid_str = params.get('dbid', [''])[0]
    if dbid_str.isdigit():
        from lib.data.api.person import library_tmdb_id
        return library_tmdb_id(dbtype, int(dbid_str)) or 0
    return 0


def handle_tmdb_recommendations(handle: int, params: dict) -> None:
    """Plugin entry for an item's TMDB recommendations, read from its complete TMDB data."""
    try:
        dbtype = params.get('dbtype', [''])[0]
        limit = int(params.get('limit', ['25'])[0])
        source = params.get('source', ['online'])[0]

        if dbtype not in ('movie', 'tvshow'):
            log("Plugin", f"TMDB Recommendations: Invalid dbtype '{dbtype}'", xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

        xbmcplugin.setPluginCategory(handle, ADDON.getLocalizedString(32682))

        tmdb_id = _seed_tmdb_id(dbtype, params)
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

        genre_map = api.get_genre_list(tmdb_type)

        normalized_recs = [_normalize_tmdb_item(raw, media_type, genre_map) for raw in recs]
        library_lookup = _get_library_lookup(
            kodi_media_type, [n.get("tmdb_id") for n in normalized_recs]
        )

        items: List[Tuple[str, xbmcgui.ListItem, bool]] = []
        for normalized in normalized_recs:
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
            xbmc.LOGDEBUG)

    except Exception as e:
        import traceback
        log("Plugin", f"TMDB Recommendations: Error - {e}", xbmc.LOGERROR)
        log("Plugin", traceback.format_exc(), xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(handle, succeeded=False)


def handle_tmdb_posters(handle: int, params: dict) -> None:
    """Plugin entry for an item's TMDB posters, the metadata language first, then English."""
    try:
        dbtype = params.get('dbtype', [''])[0]
        tmdb_id = _seed_tmdb_id(dbtype, params) if dbtype in ('movie', 'tvshow') else 0
        if not tmdb_id:
            log("Plugin", f"TMDB Posters: No tmdb_id for dbtype '{dbtype}'", xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

        from lib.data.api.tmdb import ApiTmdb
        from lib.artwork.utilities import get_language_display_name
        from lib.kodi.formatters import format_rating
        from lib.kodi.settings import KodiSettings

        data = ApiTmdb().get_complete_data(dbtype, tmdb_id)
        if not data:
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

        preferred = KodiSettings.online_metadata_language().split('-')[0]
        order = {preferred: 0, 'en': 1, '': 2}
        posters = [p for p in (data.get('images') or {}).get('posters') or []
                   if p.get('file_path') and not p['file_path'].lower().endswith('.svg')]
        posters.sort(key=lambda p: order.get(p.get('iso_639_1') or '', 3))
        images_path = sys.argv[0] + sys.argv[2]

        for poster in posters:
            language = poster.get('iso_639_1') or ''
            width = poster.get('width')
            height = poster.get('height')
            dimensions = f"{width}x{height}" if width and height else ''
            item = xbmcgui.ListItem(get_language_display_name(language), dimensions,
                                    offscreen=True)
            url = tmdb_image_url(poster['file_path'], 'w780')
            item.setArt({'thumb': url, 'poster': url, 'icon': url})
            props = {
                'language': get_language_display_name(language) if language else '',
                'language_short': language,
                'width': str(width or ''),
                'height': str(height or ''),
                'dimensions': dimensions,
                'rating': format_rating(poster.get('vote_average')),
                'votes': str(poster.get('vote_count') or ''),
                'aspectratio': str(poster.get('aspect_ratio') or ''),
                'images_path': images_path,
            }
            for key, value in props.items():
                if value:
                    item.setProperty(key, value)
            xbmcplugin.addDirectoryItem(handle, '', item, False)

        xbmcplugin.setContent(handle, 'images')
        xbmcplugin.endOfDirectory(handle, succeeded=True)

    except Exception as e:
        import traceback
        log("Plugin", f"TMDB Posters: Error - {e}", xbmc.LOGERROR)
        log("Plugin", traceback.format_exc(), xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(handle, succeeded=False)


_DISCOVER_SORTS: Final = {
    "popularity": "popularity.desc", "votes": "vote_count.desc", "revenue": "revenue.desc",
}


def _directed_movies(seed: dict) -> list:
    """Movies the seed's director directed, most popular first."""
    from lib.data.api.person import get_person_data
    crew = (seed.get("credits") or {}).get("crew") or []
    director = next((c for c in crew if c.get("job") == "Director"), None)
    if not director:
        return []
    person = get_person_data(int(director["id"])) or {}
    credits = (person.get("combined_credits") or {}).get("crew") or []
    movies = {c["id"]: c for c in credits
              if c.get("job") == "Director" and c.get("media_type") == "movie"}
    return sorted(movies.values(), key=lambda c: c.get("popularity") or 0, reverse=True)


def _seeded_results(by: str, media_type: str, seed: dict, sort: str, page: int) -> list:
    """Raw results sharing the seed's studio, network, genre, year, cast, director or collection."""
    from lib.data.api.tmdb import ApiTmdb
    api = ApiTmdb()
    if by == "director":
        return _directed_movies(seed) if media_type == "movie" else []
    if by == "collection":
        collection = seed.get("belongs_to_collection") or {}
        parts = api.get_collection(int(collection["id"])) if collection.get("id") else []
        return sorted(parts, key=lambda p: p.get("release_date") or "9999")

    filters = {"sort_by": sort}
    if by == "studio":
        ids = [str(c["id"]) for c in seed.get("production_companies") or []][:1]
        filters["with_companies"] = "".join(ids)
    elif by == "network":
        ids = [str(n["id"]) for n in seed.get("networks") or []][:1]
        filters["with_networks"] = "".join(ids)
    elif by == "genre":
        ids = [str(g["id"]) for g in seed.get("genres") or []][:1]
        filters["with_genres"] = "".join(ids)
    elif by == "year":
        year = (seed.get("release_date") or seed.get("first_air_date") or "")[:4]
        filters["primary_release_year" if media_type == "movie" else "first_air_date_year"] = year
    elif by == "cast" and media_type == "movie":
        cast = (seed.get("credits") or {}).get("cast") or []
        filters["with_cast"] = "|".join(str(c["id"]) for c in cast[:3])
    else:
        return []
    if not all(filters.values()):
        return []
    return api.discover(media_type if media_type == "movie" else "tv", filters, page)


def _genre_id(genre_map: Dict[int, str], name: str) -> Optional[int]:
    """TMDB id of a genre by name, or by the part before ` & ` a URL's `&` cuts it to."""
    wanted = name.strip().lower()
    names = {gid: label.lower() for gid, label in genre_map.items()}
    return (next((gid for gid, label in names.items() if label == wanted), None)
            or next((gid for gid, label in names.items() if label.split(' & ')[0] == wanted),
                    None))


def handle_tmdb_discover(handle: int, params: dict) -> None:
    """Plugin entry for TMDB discover: titles by seed trait or genre, or a sorted catalogue."""
    try:
        dbtype = params.get("dbtype", ["movie"])[0]
        if dbtype not in ("movie", "tvshow"):
            dbtype = "movie"
        media_type = "movie" if dbtype == "movie" else "tv"
        by = params.get("by", [""])[0]
        sort_name = params.get("sort", ["popularity"])[0]
        if sort_name == "revenue" and media_type != "movie":
            sort_name = "popularity"
        sort = _DISCOVER_SORTS.get(sort_name, _DISCOVER_SORTS["popularity"])
        limit = int(params.get("limit", ["20"])[0])
        page = int(params.get("page", ["1"])[0])
        source = params.get("source", ["online"])[0]

        genre = params.get("genre", [""])[0]

        from lib.data.api.tmdb import ApiTmdb
        api = ApiTmdb()
        genre_map = api.get_genre_list(media_type)
        seed_id = 0
        if by:
            seed_id = _seed_tmdb_id(dbtype, params)
            seed = api.get_complete_data(dbtype, seed_id) if seed_id else None
            raw_items = _seeded_results(by, media_type, seed, sort, page) if seed else []
        elif genre:
            genre_id = _genre_id(genre_map, genre)
            raw_items = api.discover(
                media_type, {"sort_by": sort, "with_genres": str(genre_id)}, page
            ) if genre_id else []
        else:
            raw_items = api.discover(media_type, {"sort_by": sort}, page)

        normalized_items = [_normalize_tmdb_item(raw, media_type, genre_map)
                            for raw in raw_items if raw.get("id") != seed_id][:limit]
        library_lookup = _get_library_lookup(
            dbtype, [n.get("tmdb_id") for n in normalized_items])

        count = 0
        for normalized in normalized_items:
            lib_match = library_lookup.get(str(normalized.get("tmdb_id", "")))
            if source == "library" and not lib_match:
                continue
            url, listitem, is_folder = _create_listitem(normalized, lib_match)
            xbmcplugin.addDirectoryItem(handle, url, listitem, is_folder)
            count += 1

        xbmcplugin.setContent(handle, "movies" if media_type == "movie" else "tvshows")
        xbmcplugin.endOfDirectory(handle, succeeded=True)
        log("Plugin", f"TMDB Discover: by={by or '-'} {dbtype} returned {count} items",
            xbmc.LOGDEBUG)

    except Exception as e:
        import traceback
        log("Plugin", f"TMDB Discover: Error - {e}", xbmc.LOGERROR)
        log("Plugin", traceback.format_exc(), xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(handle, succeeded=False)


def _discover_url(action: str, media_type: str) -> str:
    """Build the discovery widget plugin:// URL for an action and media type."""
    return f"plugin://script.skin.info.service/?action={action}&type={media_type}"


_DISCOVER_MENUS = {
    "movie": {"action": "discover_movies_menu", "label": 32625, "icon": "DefaultMovies.png"},
    "tv": {"action": "discover_tvshows_menu", "label": 32626, "icon": "DefaultTVShows.png"},
}


def handle_discover_menu(handle: int, params: dict) -> None:
    """Plugin entry for the top-level Discover menu: Movies and TV Shows."""
    xbmcplugin.setPluginCategory(handle, ADDON.getLocalizedString(32619))
    for menu in _DISCOVER_MENUS.values():
        icon = menu["icon"]
        li = xbmcgui.ListItem(ADDON.getLocalizedString(menu["label"]), offscreen=True)
        li.setArt({"icon": icon, "thumb": icon})
        xbmcplugin.addDirectoryItem(
            handle, f"plugin://script.skin.info.service/?action={menu['action']}",
            li, isFolder=True)

    xbmcplugin.endOfDirectory(handle, succeeded=True)


def _render_discover_widgets(handle: int, media: str) -> None:
    """Render every registry widget for the media type, marking the ones needing an account."""
    xbmcplugin.setPluginCategory(handle, ADDON.getLocalizedString(_DISCOVER_MENUS[media]["label"]))
    icon = _DISCOVER_MENUS[media]["icon"]
    for action, config in WIDGET_REGISTRY.items():
        if media not in config["types"]:
            continue
        label = ADDON.getLocalizedString(config["label"])
        if config.get("auth") == "oauth":
            label += " " + ADDON.getLocalizedString(32641)
        li = xbmcgui.ListItem(label, offscreen=True)
        li.setArt({"icon": icon, "thumb": icon})
        xbmcplugin.addDirectoryItem(handle, _discover_url(action, media), li, isFolder=True)

    xbmcplugin.endOfDirectory(handle, succeeded=True)


def handle_discover_movies_menu(handle: int, params: dict) -> None:
    """Plugin entry for the movies Discover menu, one row per movie widget."""
    _render_discover_widgets(handle, "movie")


def handle_discover_tvshows_menu(handle: int, params: dict) -> None:
    """Plugin entry for the TV shows Discover menu, one row per TV widget."""
    _render_discover_widgets(handle, "tv")
