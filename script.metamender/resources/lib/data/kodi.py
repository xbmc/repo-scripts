"""
Kodi JSON-RPC data access layer.

All library reads and writes go through this module.

Logging:
    Logger: 'kodi'
    Key events:
        - kodi.query (INFO): Library bulk query with count and timing
        - kodi.update (DEBUG): Field written to an item
        - kodi.update_fail (WARNING): Failed to write a field
"""
from __future__ import annotations

import json
import time
from typing import Any

import xbmc

from resources.lib.data.media_types import MOVIE, SEASON, SET, TVSHOW, MediaType
from resources.lib.engine.art import ART_FIELDS, unwrap
from resources.lib.utils import KodiQueryError, get_logger, log_timing

log = get_logger('kodi')

# Base properties requested for all media types
_BASE_PROPERTIES = [
    "title", "rating", "votes", "plot", "ratings", "uniqueid",
    "file", "dateadded",
]

# Extra properties per media type name
_EXTRA_PROPERTIES = {
    "movie": [
        "mpaa", "tagline", "director", "writer", "genre", "originaltitle",
        "studio", "country", "trailer", "runtime",
    ],
    "tvshow": [
        "mpaa", "genre", "episodeguide", "originaltitle",
    ],
    "episode": [
        "tvshowid", "showtitle", "season", "episode",
        "director", "writer", "runtime",
    ],
}

# Kodi has no rating, uniqueid or date on a season.
_SEASON_PROPERTIES = ["season", "showtitle", "tvshowid", "art", "title"]

# A set has no file, ids or date of its own: those come from its members.
_SET_PROPERTIES = ["title", "plot", "art"]

# What the set planning reads of a movie in a set (engine/sets.py).
_SET_MEMBER_PROPERTIES = ["title", "set", "setid", "file", "uniqueid", "premiered"]

# Kodi's "All seasons" pseudo-entry.
_ALL_SEASONS = -1


def _build_properties(media_type: MediaType, art: bool = True) -> list[str]:
    """Build the JSON-RPC property list for a media type.

    The base properties, the date field (premiered or firstaired), the art
    map when ``art`` is set, and the media type's extras. The art map is
    large (an episode's carries its show's and season's art too), so a
    listing for a pass that manages no art leaves it out. Seasons get their
    own short list, art included: a season is only scanned for its poster.
    Sets get theirs, art included.
    """
    if media_type is SEASON:
        return list(_SEASON_PROPERTIES)
    if media_type is SET:
        return list(_SET_PROPERTIES)
    props = list(_BASE_PROPERTIES)
    props.append(media_type.date_field)
    if art:
        props.append("art")
    props.extend(_EXTRA_PROPERTIES.get(media_type.name, []))
    return props


def flatten_art(item: dict[str, Any], media_type: MediaType) -> dict[str, Any]:
    """Expose the art slots MetaMender manages as plain top-level fields.

    Kodi returns art as a map of ``image://`` wrapped values; the engine reads
    the unwrapped URL from ``item["poster"]`` / ``item["thumb"]``.
    """
    art = item.get("art") or {}
    for field in media_type.backfill_fields & ART_FIELDS:
        item[field] = unwrap(art.get(field))
    return item


def get_all_items(
    media_type: MediaType,
    tvshowid: int | None = None,
    season: int | None = None,
    ids_only: bool = False,
    art: bool = True,
) -> list[dict[str, Any]]:
    """Query Kodi library for items of the given media type.

    Args:
        media_type: The media type to query (MOVIE, TVSHOW, SEASON or
            EPISODE).
        tvshowid: For seasons and episodes, limit to this TV show (Kodi
            param, not filter).
        season: For episodes, limit to this season (requires tvshowid).
        ids_only: Ask for no properties: each item carries only its Kodi id
            and label, which keeps a listing of a large library cheap.
        art: Ask for the art map and expose the managed art slots as
            ``poster`` / ``thumb``. Without it the items carry no art field
            at all, so nothing can read an unrequested slot as empty.

    Returns:
        List of item dicts from the Kodi library.
    """
    params: dict[str, Any] = {
        "properties": [] if ids_only else _build_properties(media_type, art),
        "limits": {"start": 0, "end": 99999},
    }
    if tvshowid is not None:
        params["tvshowid"] = tvshowid
    if season is not None:
        params["season"] = season

    query = {
        "jsonrpc": "2.0",
        "method": media_type.kodi_list_method,
        "params": params,
        "id": 1,
    }

    try:
        rpc_start = time.perf_counter()
        with log_timing(log, "get_all_items", media_type=media_type.name) as timer:
            raw = xbmc.executeJSONRPC(json.dumps(query))
            timer.mark("rpc")
            data = json.loads(raw)
            timer.mark("parse")
        rpc_ms = int((time.perf_counter() - rpc_start) * 1000)
    except Exception as exc:
        log.exception(
            "Failed to query library",
            event="kodi.query",
            media_type=media_type.name,
        )
        raise KodiQueryError(
            "JSON-RPC query failed for {}".format(media_type.name)
        ) from exc

    if "error" in data or "result" not in data:
        log.error(
            "Library query returned an error",
            event="kodi.query",
            media_type=media_type.name,
            error=str(data.get("error", "no result key")),
        )
        raise KodiQueryError(
            "JSON-RPC error response for {}".format(media_type.name)
        )

    result = data.get("result", {})
    items = result.get(media_type.kodi_result_key, [])
    if media_type is SEASON:
        items = [i for i in items if i.get("season") != _ALL_SEASONS]
    if art and not ids_only:
        for item in items:
            flatten_art(item, media_type)

    total = result.get("limits", {}).get("total", 0)
    if total >= 99999:
        log.warning(
            "Library query hit the result ceiling; some items may be missing",
            event="kodi.truncated",
            total=total,
            media_type=media_type.name,
        )

    log.info(
        "Library queried",
        event="kodi.query",
        media_type=media_type.name,
        count=len(items),
        duration_ms=rpc_ms,
    )

    return items


def get_movies_for_sets() -> list[dict[str, Any]]:
    """Every movie in the library, in a set or not (``setid`` 0), with what
    the set planning needs. Raises KodiQueryError when the listing fails: no
    answer is not the same as no movies."""
    query = {
        "jsonrpc": "2.0",
        "method": MOVIE.kodi_list_method,
        "params": {"properties": list(_SET_MEMBER_PROPERTIES),
                   "limits": {"start": 0, "end": 99999}},
        "id": 1,
    }
    try:
        data = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
    except Exception as exc:
        log.exception("Failed to query movies for sets", event="kodi.query", media_type="set")
        raise KodiQueryError("JSON-RPC query failed for movies for sets") from exc
    if "error" in data or "result" not in data:
        log.error("Movies for sets query returned an error", event="kodi.query",
                  media_type="set", error=str(data.get("error", "no result key")))
        raise KodiQueryError("JSON-RPC error response for movies for sets")
    return list(data["result"].get(MOVIE.kodi_result_key, []))


def movie_set_folder() -> str:
    """Kodi's movie set information folder (``videolibrary.moviesetsfolder``),
    "" when unset or when the setting cannot be read."""
    query = {
        "jsonrpc": "2.0",
        "method": "Settings.GetSettingValue",
        "params": {"setting": "videolibrary.moviesetsfolder"},
        "id": 1,
    }
    try:
        data = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
        value = data["result"]["value"]
    except Exception:  # noqa: BLE001  any failure means "no folder", never an error
        # DEBUG, not an error: the folder is optional, and an unreadable
        # setting only means set names are not matched to folders this scan.
        log.debug("Movie set folder setting unreadable", event="kodi.set_folder_unreadable")
        return ""
    return value if isinstance(value, str) else ""


def get_movie_setid(movieid: int) -> int | None:
    """The setid a movie sits in now (0 for none), or None when the movie
    is gone or the query failed."""
    detail = _details(MOVIE.kodi_get_method, MOVIE.kodi_id_field, movieid,
                      MOVIE.kodi_detail_key, ["setid"])
    if not detail or "setid" not in detail:
        return None
    return int(detail["setid"] or 0)


def get_seasons_for_scan(
    show_id_map: dict[int, str],
    tvshowid: int | None = None,
    show_tvdb_map: dict[int, str] | None = None,
) -> list[dict[str, Any]]:
    """The library's seasons (one show's with ``tvshowid``), ready for the
    season scan.

    Kodi gives a season no file and no ids, so each carries its show's: the
    show folder as ``file`` (which places it in a library and holds the
    tvshow.nfo that governs it), and ``show_tmdb_id`` / ``show_tvdb_id`` from
    the tracker's show maps, None when unknown. A season of a show Kodi did
    not list keeps an empty ``file``. ``show_seasons`` lists the season
    numbers Kodi has for that show ("All seasons" excluded), the reference
    for the fanart.tv season poster tie-break.
    """
    if tvshowid is None:
        shows = get_all_items(TVSHOW, art=False)
    else:
        show = get_item_by_id(TVSHOW, tvshowid, art=False)
        shows = [show] if show else []
    folders = {s.get("tvshowid"): str(s.get("file") or "") for s in shows}
    tvdb_map = show_tvdb_map or {}
    seasons = get_all_items(SEASON, tvshowid=tvshowid)
    numbers: dict[int, list[int]] = {}
    for season in seasons:
        number = int(season.get("season", 0) or 0)
        if number != _ALL_SEASONS:
            numbers.setdefault(int(season.get("tvshowid", -1)), []).append(number)
    for season in seasons:
        show_id = int(season.get("tvshowid", -1))
        season["show_seasons"] = sorted(numbers.get(show_id, []))
        season["file"] = folders.get(show_id, "")
        season["show_tmdb_id"] = show_id_map.get(show_id)
        season["show_tvdb_id"] = tvdb_map.get(show_id)
    return seasons


def get_item_by_id(
    media_type: MediaType,
    item_id: int,
    art: bool = True,
) -> dict[str, Any] | None:
    """Fetch a single library item by its Kodi database ID.

    Uses GetXDetails with the same property set as get_all_items, so the
    returned item has every field the scan engine expects. Returns None if
    the item does not exist or the query fails (the caller decides how to
    surface that to the user).

    Args:
        media_type: The media type to query (MOVIE, TVSHOW, SEASON or
            EPISODE).
        item_id: The Kodi database ID for the item.
        art: As for get_all_items.

    Returns:
        The item dict, or None when not found / on error.
    """
    properties = _build_properties(media_type, art)
    params: dict[str, Any] = {
        media_type.kodi_id_field: item_id,
        "properties": properties,
    }

    query = {
        "jsonrpc": "2.0",
        "method": media_type.kodi_get_method,
        "params": params,
        "id": 1,
    }

    try:
        raw = xbmc.executeJSONRPC(json.dumps(query))
        data = json.loads(raw)
    except Exception:
        log.exception(
            "Failed to query item by id",
            event="kodi.query",
            media_type=media_type.name,
            item_id=item_id,
        )
        return None

    if "error" in data or "result" not in data:
        log.warning(
            "Item-by-id query returned an error",
            event="kodi.query",
            media_type=media_type.name,
            item_id=item_id,
            error=str(data.get("error", "no result key")),
        )
        return None

    detail = data.get("result", {}).get(media_type.kodi_detail_key)
    if not detail:
        return None
    return flatten_art(detail, media_type) if art else detail


def _details(method: str, id_field: str, item_id: int, key: str,
             properties: list[str]) -> dict[str, Any] | None:
    """One GetXDetails call returning the detail dict, or None when the item
    does not exist or the query fails."""
    query = {"jsonrpc": "2.0", "method": method, "id": 1,
             "params": {id_field: item_id, "properties": properties}}
    try:
        data = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
    except Exception:
        log.exception("Failed to query item details", event="kodi.query",
                      method=method, item_id=item_id)
        return None
    detail = (data.get("result") or {}).get(key)
    return detail or None


def get_season_info(seasonid: int) -> tuple[int, int] | None:
    """The show id and season number of a season node, or None."""
    detail = _details("VideoLibrary.GetSeasonDetails", "seasonid", seasonid,
                      "seasondetails", ["tvshowid", "season"])
    if not detail or "tvshowid" not in detail or "season" not in detail:
        return None
    return int(detail["tvshowid"]), int(detail["season"])


def get_episode_show_id(episodeid: int) -> int | None:
    """The show id of an episode, or None."""
    detail = _details("VideoLibrary.GetEpisodeDetails", "episodeid", episodeid,
                      "episodedetails", ["tvshowid"])
    if not detail or "tvshowid" not in detail:
        return None
    return int(detail["tvshowid"])


def file_runtime(media_type: MediaType, item_id: int) -> int | None:
    """The runtime Kodi shows for a movie or episode when it is the video
    file's own length, in seconds; None when Kodi shows the library's value
    or the query fails.

    Kodi keeps the library's runtime apart from the length it read from the
    file and reports the file's, unless that is under 60% of the library's
    (CVideoInfoTag::GetDuration). A listing without stream details carries
    the library's value only, so this is asked per item; a runtime equal to
    the file's length is the one Kodi shows.
    """
    detail = _details(media_type.kodi_get_method, media_type.kodi_id_field, item_id,
                      media_type.kodi_detail_key, ["runtime", "streamdetails"])
    if not detail:
        return None
    video = (detail.get("streamdetails") or {}).get("video") or []
    try:
        length = int(video[0].get("duration") or 0) if video else 0
        shown = int(detail.get("runtime") or 0)
    except (TypeError, ValueError, AttributeError):
        return None
    return length if length > 0 and shown == length else None


def update_item(
    item_id: int,
    media_type: MediaType,
    log_title: str = "",
    **fields: Any,
) -> bool:
    """Write fields back to a Kodi library item via JSON-RPC.

    Args:
        item_id: The Kodi database ID for the item.
        media_type: The media type of the item.
        log_title: The item title (for logging only, not written to Kodi).
        **fields: Field names and values to set (including "title" for
            episodes). The art fields (``poster``, ``thumb``) are sent in
            Kodi's ``art`` map, an empty value as null, which clears the slot.

    Returns:
        True on success, False on failure.
    """
    params: dict[str, Any] = {media_type.kodi_id_field: item_id}
    art = {f: (fields.pop(f) or None) for f in ART_FIELDS & fields.keys()}
    params.update(fields)
    if art:
        # An empty string clears the slot: Kodi removes a key set to null.
        params["art"] = art

    query = {
        "jsonrpc": "2.0",
        "method": media_type.kodi_set_method,
        "params": params,
        "id": 1,
    }

    try:
        with log_timing(log, "update_item", media_type=media_type.name, title=log_title):
            raw = xbmc.executeJSONRPC(json.dumps(query))
            data = json.loads(raw)
    except Exception:
        log.exception(
            "Failed to update item",
            event="kodi.update_fail",
            media_type=media_type.name,
            title=log_title,
            item_id=item_id,
        )
        return False

    if "error" in data:
        log.warning(
            "Failed to update item",
            event="kodi.update_fail",
            media_type=media_type.name,
            title=log_title,
            item_id=item_id,
            error=str(data["error"]),
        )
        return False

    # Kodi's Set*Details returns {"result": "OK"} on success. Treat anything
    # else (a missing or non-"OK" result) as a failed write rather than
    # assuming success from the mere absence of an error key.
    if data.get("result") != "OK":
        log.warning(
            "Update returned a non-OK result",
            event="kodi.update_fail",
            media_type=media_type.name,
            title=log_title,
            item_id=item_id,
            result=str(data.get("result")),
        )
        return False

    log.debug(
        "Item updated",
        event="kodi.update",
        media_type=media_type.name,
        title=log_title,
        item_id=item_id,
        fields=", ".join(fields.keys()),
    )
    return True
