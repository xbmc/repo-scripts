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

from resources.lib.data.media_types import MediaType
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


def _build_properties(media_type: MediaType) -> list[str]:
    """Build the JSON-RPC property list for a media type.

    Combines the base properties with media-type-specific extras
    and the date field (premiered or firstaired).
    """
    props = list(_BASE_PROPERTIES)
    props.append(media_type.date_field)
    extras = _EXTRA_PROPERTIES.get(media_type.name, [])
    props.extend(extras)
    return props


def get_all_items(
    media_type: MediaType,
    tvshowid: int | None = None,
    season: int | None = None,
    ids_only: bool = False,
) -> list[dict[str, Any]]:
    """Query Kodi library for items of the given media type.

    Args:
        media_type: The media type to query (MOVIE, TVSHOW, or EPISODE).
        tvshowid: For episodes, limit to this TV show (Kodi param, not filter).
        season: For episodes, limit to this season (requires tvshowid).
        ids_only: Ask for no properties: each item carries only its Kodi id
            and label, which keeps a listing of a large library cheap.

    Returns:
        List of item dicts from the Kodi library.
    """
    params: dict[str, Any] = {
        "properties": [] if ids_only else _build_properties(media_type),
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


def get_item_by_id(
    media_type: MediaType,
    item_id: int,
) -> dict[str, Any] | None:
    """Fetch a single library item by its Kodi database ID.

    Uses GetXDetails with the same property set as get_all_items, so the
    returned item has every field the scan engine expects. Returns None if
    the item does not exist or the query fails (the caller decides how to
    surface that to the user).

    Args:
        media_type: The media type to query (MOVIE, TVSHOW, or EPISODE).
        item_id: The Kodi database ID for the item.

    Returns:
        The item dict, or None when not found / on error.
    """
    properties = _build_properties(media_type)
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
    return detail


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
        **fields: Field names and values to set (including "title" for episodes).

    Returns:
        True on success, False on failure.
    """
    params = {media_type.kodi_id_field: item_id}
    params.update(fields)

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
