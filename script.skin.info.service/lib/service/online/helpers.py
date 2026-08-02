"""Online service helpers: cache key, TTL derivation, ID resolution."""
from __future__ import annotations

from typing import Dict, Tuple

import xbmc

from lib.kodi.utilities import get_prop
from lib.data.database.cache import invalidate_online_properties


SKININFO_PREFIX_MAP = {
    "movie": "SkinInfo.Movie",
    "tvshow": "SkinInfo.TVShow",
    "episode": "SkinInfo.Episode",
}

PLAYER_SKININFO_PREFIX_MAP = {
    "movie": "SkinInfo.Player",
    "episode": "SkinInfo.Player",
}


def get_online_ttl(media_type: str, tmdb_id: str) -> int:
    """Derive smart TTL from cached TMDB metadata for online properties cache."""
    from lib.data.database.cache import get_cached_metadata, get_cache_ttl_hours

    tmdb_data = get_cached_metadata(media_type, tmdb_id)
    if not tmdb_data:
        return 72

    hints: Dict[str, str] = {}
    status = tmdb_data.get("status") or ""
    if status:
        hints["status"] = status

    next_ep = tmdb_data.get("next_episode_to_air")
    if isinstance(next_ep, dict) and next_ep.get("air_date"):
        next_ep_complete = bool(next_ep.get("name") and next_ep.get("overview"))
        if next_ep_complete:
            hints["next_episode_air_date"] = next_ep["air_date"]
        else:
            hints["next_episode_air_date_incomplete"] = next_ep["air_date"]

    if media_type == "tvshow":
        has_overview = bool(tmdb_data.get("overview"))
        has_cast = len(tmdb_data.get("credits", {}).get("cast", [])) > 0
        has_imdb = bool((tmdb_data.get("external_ids") or {}).get("imdb_id"))
        has_content_ratings = len(tmdb_data.get("content_ratings", {}).get("results", [])) > 0
        last_ep = tmdb_data.get("last_episode_to_air")
        has_last_ep = bool(last_ep and last_ep.get("overview"))
        if has_overview and has_cast and has_imdb and has_content_ratings and has_last_ep:
            hints["aired_data_complete"] = "true"
        if isinstance(last_ep, dict) and last_ep.get("air_date"):
            hints["last_air_date"] = last_ep["air_date"]

    release_date = tmdb_data.get("release_date") or tmdb_data.get("first_air_date")
    return get_cache_ttl_hours(release_date, hints)


def invalidate_online_cache(media_type: str, imdb_id: str = '', tmdb_id: str = '') -> None:
    """Invalidate the online properties cache for a specific library item."""
    invalidate_online_properties(media_type, imdb_id=imdb_id, tmdb_id=tmdb_id)


def invalidate_online_cache_for_dbid(media_type: str, dbid: str) -> None:
    """Resolve uniqueids for a library item and drop its cached online data."""
    from lib.kodi.client import get_item_uniqueids
    imdb_id, tmdb_id = get_item_uniqueids(media_type, dbid)
    if imdb_id or tmdb_id:
        invalidate_online_properties(media_type, imdb_id=imdb_id, tmdb_id=tmdb_id)


def make_cache_key(media_type: str, imdb_id: str, tmdb_id: str) -> str:
    """Build a stable cache key. TMDB preferred (earlier-resolved, consistent), IMDb fallback."""
    if tmdb_id:
        return f"{media_type}:tmdb:{tmdb_id}"
    if imdb_id:
        return f"{media_type}:imdb:{imdb_id}"
    return ""


def resolve_ids_from(dbtype: str, dbid: str, info_prefix: str,
                     prefix_map: Dict[str, str]) -> Tuple[str, str]:
    """Resolve `(imdb_id, tmdb_id)`: InfoLabel -> SkinInfo props -> ID map -> JSON-RPC fallback."""
    imdb_id = xbmc.getInfoLabel(f"{info_prefix}.UniqueID(imdb)") or ""
    tmdb_id = xbmc.getInfoLabel(f"{info_prefix}.UniqueID(tmdb)") or ""

    if not imdb_id:
        imdbnumber = xbmc.getInfoLabel(f"{info_prefix}.IMDBNumber") or ""
        if imdbnumber.startswith("tt"):
            imdb_id = imdbnumber

    if not imdb_id or not tmdb_id:
        prefix = prefix_map.get(dbtype, "")
        if prefix:
            if not imdb_id:
                imdb_id = get_prop(f"{prefix}.UniqueID.IMDB") or ""
            if not tmdb_id:
                tmdb_id = get_prop(f"{prefix}.UniqueID.TMDB") or ""

    if not imdb_id and tmdb_id:
        from lib.data.database.mapping import get_imdb_id
        cache_type = "tvshow" if dbtype == "episode" else dbtype
        imdb_id = get_imdb_id(tmdb_id, cache_type) or ""

    if not imdb_id and not tmdb_id:
        from lib.kodi.client import get_item_uniqueids
        imdb_id, tmdb_id = get_item_uniqueids(dbtype, dbid)

    return imdb_id, tmdb_id


def resolve_season_ids(seasonid: str) -> Tuple[str, str]:
    """Resolve IMDb/TMDb IDs for a season via its parent tvshow."""
    from lib.kodi.client import get_item_details, get_item_uniqueids
    details = get_item_details('season', int(seasonid), ["tvshowid"])
    if not details or not isinstance(details, dict):
        return "", ""
    tvshowid = details.get("tvshowid")
    if not tvshowid or tvshowid == -1:
        return "", ""
    return get_item_uniqueids("tvshow", str(tvshowid))
