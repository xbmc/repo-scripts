"""Live TV match picker: the user fixes a programme's TMDB title, or says it has none."""
from __future__ import annotations

from typing import List, Optional

import xbmc
import xbmcaddon
import xbmcgui

from lib.kodi.client import log, request
from lib.infrastructure.dialogs import show_notification, show_select
from lib.data.api.utilities import tmdb_image_url
from lib.data.database.cache import CacheKey, cache_online_properties
from lib.data.database.pvr import (
    PVR_SCOPE, PvrMatch, get_pvr_match, save_pvr_match,
)
from lib.data.online import get_online_ttl
from lib.data.pvr import (
    MATCH_CHANGED, PvrTitle, fetch_programme_props, focused_programme, match_key,
    programme_candidates,
)

ADDON = xbmcaddon.Addon()


def _media_type(result: dict) -> str:
    """Library media type of a search result."""
    return "movie" if result.get("media_type") == "movie" else "tvshow"


def _candidate_item(result: dict) -> xbmcgui.ListItem:
    """Select-list row for a search result: title, year, type, overview and poster."""
    title = result.get("title") or result.get("name") or ""
    date = result.get("release_date") or result.get("first_air_date") or ""
    item = xbmcgui.ListItem(f"{title} ({date[:4]})" if date[:4] else title, offscreen=True)
    kind = xbmc.getLocalizedString(20338 if _media_type(result) == "movie" else 20364)
    item.setLabel2(f"{kind} - {result.get('overview') or ''}".rstrip(" -"))
    poster = tmdb_image_url(result.get("poster_path") or "", "w185")
    if poster:
        item.setArt({"thumb": poster, "icon": poster})
    return item


def _preselect(candidates: List[dict], match: Optional[PvrMatch]) -> int:
    """Row of the programme's current match, the no-match row for a manual none, else -1."""
    if not match:
        return -1
    if not match.tmdb_id:
        return 0 if match.manual else -1
    for row, result in enumerate(candidates, start=1):
        if result.get("id") == match.tmdb_id and _media_type(result) == match.media_type:
            return row
    return -1


def fix_match() -> None:
    """Fix the focused programme's match by hand: the user picks its TMDB title, or none."""
    programme = focused_programme()
    key = match_key(programme) if programme else None
    if not programme or not key:
        return

    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    try:
        candidates = programme_candidates(programme)
    except Exception as e:
        log("Service", f"PVR match search failed: {e}", xbmc.LOGWARNING)
        candidates = []
    finally:
        xbmc.executebuiltin('Dialog.Close(busydialognocancel,true)')
    if not candidates:
        show_notification(xbmc.getLocalizedString(137), xbmc.getLocalizedString(284))
        return

    rows = [xbmcgui.ListItem(xbmc.getLocalizedString(231), offscreen=True)]
    rows += [_candidate_item(result) for result in candidates]
    choice = show_select(ADDON.getLocalizedString(32079), rows,
                         _preselect(candidates, get_pvr_match(key)), use_details=True)
    if choice < 0:
        return

    if choice == 0:
        save_pvr_match(key, "", 0, manual=True)
    else:
        picked = candidates[choice - 1]
        title = PvrTitle(_media_type(picked), int(picked["id"]))
        save_pvr_match(key, title.media_type, title.tmdb_id, manual=True)
        xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
        try:
            props = fetch_programme_props(title)
            if props:
                cache_online_properties(
                    CacheKey(title.media_type, str(title.tmdb_id), PVR_SCOPE), props,
                    ttl_hours=get_online_ttl(title.media_type, str(title.tmdb_id)))
        finally:
            xbmc.executebuiltin('Dialog.Close(busydialognocancel,true)')
    request("JSONRPC.NotifyAll", {"sender": ADDON.getAddonInfo("id"), "message": MATCH_CHANGED})
