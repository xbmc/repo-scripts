"""Online service helpers: item ids from the InfoLabels, and dropping an item's online cache."""
from __future__ import annotations

from typing import Callable, Tuple

import xbmc

from lib.data.database.cache import invalidate_online_properties


def invalidate_online_cache_for_dbid(media_type: str, dbid: str) -> None:
    """Resolve uniqueids for a library item and drop its cached online data."""
    from lib.kodi.client import get_item_uniqueids
    imdb_id, tmdb_id = get_item_uniqueids(media_type, dbid)
    if imdb_id or tmdb_id:
        invalidate_online_properties(media_type, imdb_id=imdb_id, tmdb_id=tmdb_id)


def infolabel_imdb_id(info_prefix: str,
                      read: Callable[[str], str] = xbmc.getInfoLabel) -> str:
    """IMDb id from the InfoLabels; `IMDBNumber` holds the default id, which may be another kind."""
    imdb_id = read(f"{info_prefix}.UniqueID(imdb)") or ""
    if not imdb_id:
        imdbnumber = read(f"{info_prefix}.IMDBNumber") or ""
        if imdbnumber.startswith("tt"):
            imdb_id = imdbnumber
    return imdb_id


def unlisted_ids(scoped: bool, read: Callable[[str], str]) -> Tuple[str, str]:
    """Ids a focused item outside the library carries, its show's for a season or episode."""
    if scoped:
        imdb_id = (read("ListItem.UniqueID(tvshow.imdb)")
                   or read("ListItem.Property(tvshow.imdb_id)"))
        tmdb_id = (read("ListItem.UniqueID(tvshow.tmdb)")
                   or read("ListItem.Property(tvshow.tmdb_id)"))
    else:
        imdb_id = infolabel_imdb_id("ListItem", read)
        tmdb_id = read("ListItem.UniqueID(tmdb)") or read("ListItem.Property(tmdb_id)")
    return (imdb_id if imdb_id.startswith("tt") else "",
            tmdb_id if tmdb_id.isdigit() else "")


def resolve_ids_from(dbtype: str, dbid: str, info_prefix: str,
                     read: Callable[[str], str] = xbmc.getInfoLabel) -> Tuple[str, str]:
    """Resolve `(imdb_id, tmdb_id)`: InfoLabel -> ID map -> JSON-RPC fallback."""
    imdb_id = infolabel_imdb_id(info_prefix, read)
    tmdb_id = read(f"{info_prefix}.UniqueID(tmdb)") or ""

    if not imdb_id and tmdb_id:
        from lib.data.database.mapping import get_imdb_id
        cache_type = "tvshow" if dbtype == "episode" else dbtype
        imdb_id = get_imdb_id(tmdb_id, cache_type) or ""

    if not imdb_id and not tmdb_id:
        from lib.kodi.client import get_item_uniqueids
        imdb_id, tmdb_id = get_item_uniqueids(dbtype, dbid)

    return imdb_id, tmdb_id


def resolve_show_ids(dbtype: str, dbid: str, info_prefix: str,
                     read: Callable[[str], str] = xbmc.getInfoLabel) -> Tuple[str, str]:
    """Resolve the parent show's `(imdb_id, tmdb_id)` for a season or episode."""
    from lib.kodi.client import get_item_details, get_item_uniqueids
    tvshowid = read(f"{info_prefix}.TvShowDBID") or ""
    if not tvshowid or tvshowid == "-1":
        details = get_item_details(dbtype, int(dbid), ["tvshowid"])
        if not details or not isinstance(details, dict):
            return "", ""
        tvshowid = str(details.get("tvshowid") or "")
    if not tvshowid or tvshowid == "-1":
        return "", ""
    return get_item_uniqueids("tvshow", tvshowid, cache_key=f"tvshow:{tvshowid}:uniqueid")
