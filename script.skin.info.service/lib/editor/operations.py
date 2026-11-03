"""JSON-RPC operations for metadata editor."""
from __future__ import annotations

import re
from typing import Any

import xbmc

from lib.kodi.client import (
    KODI_GET_DETAILS_METHODS,
    KODI_SET_DETAILS_METHODS,
    extract_result,
    log,
    request,
)
from lib.editor.config import get_field_def, get_properties_for_media_type


def get_item_for_editing(dbid: int, media_type: str) -> dict[str, Any] | None:
    """Get the item with every editable property, None when Kodi does not return it."""
    method_info = KODI_GET_DETAILS_METHODS.get(media_type)
    if not method_info:
        log("Editor", f"Unknown media type: {media_type}", xbmc.LOGWARNING)
        return None

    method, id_key, result_key = method_info
    properties = get_properties_for_media_type(media_type)

    response = request(method, {id_key: dbid, "properties": properties})
    result = extract_result(response, result_key)

    if not result or not isinstance(result, dict):
        log("Editor", f"Failed to fetch {media_type} {dbid}", xbmc.LOGWARNING)
        return None

    return result


def save_field(
    dbid: int, media_type: str, field_name: str, value: Any,
    item: dict[str, Any] | None = None
) -> bool:
    """Save one field to Kodi, setting premiered alongside year for a video item."""
    method_info = KODI_SET_DETAILS_METHODS.get(media_type)
    if not method_info:
        log("Editor", f"Cannot save - unknown media type: {media_type}", xbmc.LOGWARNING)
        return False

    field_def = get_field_def(field_name)
    if not field_def:
        log("Editor", f"Cannot save - unknown field: {field_name}", xbmc.LOGWARNING)
        return False

    method, id_key = method_info
    api_name = field_def["api_name"]

    params: dict[str, Any] = {id_key: dbid, api_name: value}

    # a song's mood is one string, read back split on Kodi's music item separator
    if media_type == "song" and api_name == "mood" and isinstance(value, list):
        params["mood"] = " / ".join(value)

    # Kodi ignores year when premiered is set
    if field_name == "year" and isinstance(value, int) and media_type in (
        "movie", "tvshow", "episode", "musicvideo"
    ):
        original = item.get("premiered", "") if item else ""
        if original and re.match(r'^\d{4}-\d{2}-\d{2}', original):
            params["premiered"] = f"{value}{original[4:10]}"
        else:
            params["premiered"] = f"{value}-01-01"

    response = request(method, params)

    if response is not None:
        log("Editor", f"Saved {media_type} {dbid} {field_name}", xbmc.LOGDEBUG)
        return True

    log("Editor", f"Failed to save {media_type} {dbid} {field_name}", xbmc.LOGWARNING)
    return False


def fetch_library_genres(media_type: str) -> list[str]:
    """Fetch existing genres from library."""
    if media_type in ("movie", "tvshow", "musicvideo"):
        response = request("VideoLibrary.GetGenres", {"type": media_type})
        genres = extract_result(response, "genres", [])
    elif media_type in ("artist", "album", "song"):
        response = request("AudioLibrary.GetGenres", {})
        genres = extract_result(response, "genres", [])
    else:
        return []

    if not genres:
        return []

    return [g.get("label", "") for g in genres if g.get("label")]


def fetch_library_tags(media_type: str) -> list[str]:
    """Fetch existing tags from library."""
    if media_type not in ("movie", "tvshow", "musicvideo"):
        return []
    response = request("VideoLibrary.GetTags", {"type": media_type})
    tags = extract_result(response, "tags", [])

    if not tags:
        return []

    return [t.get("label", "") for t in tags if t.get("label")]


def _aggregate_field_values(media_type: str, field: str) -> list[str]:
    """Aggregate a field's unique values across every library item."""
    method_map = {
        "movie": ("VideoLibrary.GetMovies", "movies"),
        "tvshow": ("VideoLibrary.GetTVShows", "tvshows"),
        "musicvideo": ("VideoLibrary.GetMusicVideos", "musicvideos"),
        "episode": ("VideoLibrary.GetEpisodes", "episodes"),
        "artist": ("AudioLibrary.GetArtists", "artists"),
        "album": ("AudioLibrary.GetAlbums", "albums"),
        "song": ("AudioLibrary.GetSongs", "songs"),
    }

    method_info = method_map.get(media_type)
    if not method_info:
        return []

    method, result_key = method_info
    response = request(method, {"properties": [field]})
    items = extract_result(response, result_key, [])

    if not items:
        return []

    values: set[str] = set()
    for item in items:
        field_values = item.get(field, [])
        if isinstance(field_values, list):
            values.update(v for v in field_values if v)
        elif field_values:
            values.add(field_values)

    return sorted(values)


def fetch_library_values_for_field(
    field_name: str, media_type: str
) -> list[str]:
    """Fetch existing library values for a list field."""
    field_def = get_field_def(field_name)
    api_name = field_def["api_name"] if field_def else field_name

    if api_name == "genre":
        return fetch_library_genres(media_type)

    if api_name == "tag":
        return fetch_library_tags(media_type)

    if api_name in ("studio", "director", "writer", "country", "artist",
                    "style", "mood", "instrument", "yearsactive", "theme"):
        return _aggregate_field_values(media_type, api_name)

    return []
