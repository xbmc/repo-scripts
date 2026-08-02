"""User-triggered bulk sync of TMDB metadata for every TV show in the library."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import xbmc
import xbmcgui

from lib.kodi.client import log, ADDON, request, extract_result
from lib.data.api.tmdb import resolve_tmdb_id
from lib.data.database.cache import (
    cache_online_properties,
    get_cached_metadata,
    get_cached_online_keys,
    get_cached_online_properties,
)
from lib.data.database.mapping import get_imdb_ids_batch
from lib.data.database.schedule import upsert_schedule
from lib.infrastructure import tasks as task_manager
from lib.infrastructure.dialogs import ProgressDialog
from lib.infrastructure.menus import confirm_cancel_running_task
from lib.service.online.fetchers import fetch_tmdb_online_data
from lib.service.online.helpers import get_online_ttl, make_cache_key


def run_sync_tvshows() -> None:
    """Confirm, then iterate all library TV shows and fetch any missing TMDB metadata."""
    dialog = xbmcgui.Dialog()

    if not dialog.yesno(
        ADDON.getLocalizedString(32988),
        ADDON.getLocalizedString(32989),
    ):
        return

    operation_name = ADDON.getLocalizedString(32988)

    if task_manager.is_task_running():
        if not confirm_cancel_running_task(operation_name):
            return
        task_manager.cancel_task()
        monitor = xbmc.Monitor()
        while task_manager.is_task_running() and not monitor.abortRequested():
            monitor.waitForAbort(0.1)

    progress = None
    try:
        with task_manager.TaskContext(operation_name) as ctx:
            progress = ProgressDialog(use_background=False, heading=operation_name)
            progress.create("")
            stats = _execute_sync(progress, ctx)
            progress.close()

        cancelled = stats.get("cancelled", False)
        title = operation_name
        message = ADDON.getLocalizedString(32991).format(
            stats["fetched"], stats["skipped"], stats["failed"],
        )
        if cancelled:
            message = f"{message}[CR][CR][B]Cancelled[/B]"
        dialog.ok(title, message)

    except Exception as e:
        if progress:
            try:
                progress.close()
            except Exception:
                pass
        log("Plugin", f"Sync TV shows failed: {e}", xbmc.LOGERROR)
        dialog.ok(operation_name, str(e))


def _execute_sync(progress: ProgressDialog, ctx: task_manager.TaskContext) -> Dict[str, int]:
    stats = {"fetched": 0, "skipped": 0, "failed": 0, "cancelled": False}
    monitor = xbmc.Monitor()
    today = datetime.now().strftime("%Y-%m-%d")

    progress.update(0, "Scanning library...")
    library_shows = _get_all_library_shows()
    total_library = len(library_shows)
    if total_library == 0:
        return stats

    progress.update(2, f"Found {total_library} TV shows. Identifying uncached...")
    cached_keys = get_cached_online_keys()
    imdb_map = get_imdb_ids_batch(
        {s["tmdb_id"] for s in library_shows}, "tvshow"
    )

    work: List[Dict] = []
    for s in library_shows:
        imdb_id = imdb_map.get(s["tmdb_id"], s.get("imdb_id") or "")
        cache_key = make_cache_key("tvshow", imdb_id, s["tmdb_id"])
        if cache_key in cached_keys:
            stats["skipped"] += 1
            continue
        work.append({**s, "imdb_id": imdb_id, "cache_key": cache_key})

    if not work:
        progress.update(100, "All TV shows already cached.")
        return stats

    total_work = len(work)
    log("Plugin", f"Sync TV shows: fetching {total_work} of {total_library}", xbmc.LOGINFO)

    for i, show in enumerate(work):
        if monitor.abortRequested() or ctx.abort_flag.is_requested() or progress.is_cancelled():
            stats["cancelled"] = True
            break

        percent = int((i / total_work) * 100)
        progress.update(percent, ADDON.getLocalizedString(32990).format(i + 1, total_work))

        tmdb_id = show["tmdb_id"]
        imdb_id = show["imdb_id"]
        cache_key = show["cache_key"]

        try:
            tmdb_props = fetch_tmdb_online_data("tvshow", imdb_id, tmdb_id)
            if not tmdb_props:
                stats["failed"] += 1
                continue
            existing = get_cached_online_properties(cache_key) or {}
            existing.update(tmdb_props)
            ttl = get_online_ttl("tvshow", tmdb_id)
            cache_online_properties(cache_key, existing, ttl_hours=ttl)
            stats["fetched"] += 1

            tmdb_data = get_cached_metadata("tvshow", tmdb_id)
            if tmdb_data:
                next_ep = tmdb_data.get("next_episode_to_air")
                if next_ep and (next_ep.get("air_date") or "") < today:
                    next_ep = None
                upsert_schedule(
                    tmdb_id, show["tvshowid"], show["title"],
                    tmdb_data.get("status") or "",
                    next_ep,
                    tmdb_data.get("last_episode_to_air"),
                )
        except Exception as e:
            log("Plugin", f"Sync TV shows: error for tmdb_id={tmdb_id}: {e}", xbmc.LOGWARNING)
            stats["failed"] += 1

    if not stats["cancelled"]:
        progress.update(100, "")

    return stats


def _get_all_library_shows() -> List[Dict]:
    """Return all library TV shows resolved to TMDb IDs. Skips entries we can't resolve."""
    resp = request("VideoLibrary.GetTVShows", {
        "properties": ["title", "uniqueid"],
    })
    shows = extract_result(resp, "tvshows")
    result = []
    for s in shows:
        uid = s.get("uniqueid") or {}
        tmdb_id = uid.get("tmdb") or ""
        imdb_id = uid.get("imdb") or ""
        if not tmdb_id:
            resolved = resolve_tmdb_id("", imdb_id, "tvshow")
            if resolved:
                tmdb_id = resolved
            else:
                continue
        result.append({
            "tmdb_id": tmdb_id,
            "imdb_id": imdb_id,
            "tvshowid": s.get("tvshowid", 0),
            "title": s.get("title") or "",
        })
    return result
