"""Ratings updater orchestrator: full-library update, per-show update, batch coordination."""
from __future__ import annotations

from typing import Dict, List, Set
import time

import xbmc
import xbmcgui

from lib.infrastructure import tasks as task_manager
from lib.kodi.client import request, get_library_items, log, ADDON
from lib.data.api.imdb import get_imdb_dataset
from lib.data.api import tracker as usage_tracker
from lib.data.database import workflow as db
from lib.infrastructure.dialogs import show_ok, show_notification, ProgressDialog, DialogProgress
from lib.rating.executor import RetryPoolEntry
from lib.rating.ids import (
    clear_tvshow_uniqueid_cache,
    prefetch_tvshow_uniqueids,
)
from lib.rating.single import update_single_item
from lib.rating.imdb import (
    run_imdb_batch,
    ensure_episode_dataset,
    prompt_imdb_corrections,
)
from lib.rating.batch import MdblistBatchFetcher, run_multi_source_batch
from lib.rating.retry import prompt_and_process_retries


def update_tvshow_episodes(tvshow_dbid: int, sources: List) -> int:
    """Update ratings for every episode of a show. Returns count actually updated."""
    response = request("VideoLibrary.GetEpisodes", {
        "tvshowid": tvshow_dbid,
        "properties": ["title", "season", "episode", "tvshowid", "uniqueid", "ratings"]
    })

    if not response or "episodes" not in response.get("result", {}):
        return 0

    episodes = response["result"]["episodes"]
    if not episodes:
        return 0

    log("Ratings", f"Updating ratings for {len(episodes)} episodes", xbmc.LOGINFO)

    abort_flag = task_manager.ShutdownAbortFlag()
    updated_count = 0
    total = len(episodes)
    progress = ProgressDialog(heading=ADDON.getLocalizedString(32300))
    progress.create(ADDON.getLocalizedString(32402))
    try:
        for idx, episode in enumerate(episodes):
            if progress.is_cancelled():
                abort_flag.request()
                break
            progress.update(int(idx / total * 100),
                            episode.get("label") or episode.get("title", ""))
            success, _ = update_single_item(episode, "episode", sources, abort_flag)
            if success:
                updated_count += 1
    finally:
        progress.close()

    return updated_count


def update_library_ratings(
    media_type: str,
    sources: List,
    use_background: bool = False,
    source_mode: str = "multi_source"
) -> Dict[str, int]:
    """Update ratings for all items of a media type."""
    start_time = time.time()
    usage_tracker.reset_session_skip()

    if media_type == "episode":
        clear_tvshow_uniqueid_cache()
        properties = ["title", "season", "episode", "tvshowid", "uniqueid", "ratings"]
    else:
        properties = ["title", "year", "uniqueid", "ratings"]

    heading = ADDON.getLocalizedString(32318 if source_mode == "imdb" else 32300)
    progress: xbmcgui.DialogProgress | xbmcgui.DialogProgressBG
    if use_background:
        progress = xbmcgui.DialogProgressBG()
        progress.create(heading, ADDON.getLocalizedString(32303).format(media_type))
    else:
        progress = DialogProgress()
        progress.create(heading, ADDON.getLocalizedString(32303).format(media_type))

    items = get_library_items([media_type], properties=properties)
    if not items:
        if progress:
            progress.close()
        show_notification(
            heading,
            ADDON.getLocalizedString(32413).format(media_type),
            xbmcgui.NOTIFICATION_INFO,
            3000
        )
        return {"updated": 0, "failed": 0, "skipped": 0}

    if isinstance(progress, xbmcgui.DialogProgressBG):
        progress.update(0, heading, ADDON.getLocalizedString(32304).format(len(items), media_type))
    elif isinstance(progress, xbmcgui.DialogProgress):
        progress.update(0, ADDON.getLocalizedString(32304).format(len(items), media_type))

    results: Dict = {
        "updated": 0, "failed": 0, "skipped": 0,
        "total_items": len(items), "source_stats": {}, "item_details": [],
        "total_ratings_added": 0, "total_ratings_updated": 0,
        "imdb_ids_added": 0, "imdb_ids_corrected": 0,
        "pending_corrections": [], "source_mode": source_mode,
    }

    retry_queue: List[RetryPoolEntry] = []
    dataset_date: str = ""
    processed_ids: Set[int] = set()

    if source_mode == "imdb":
        dataset = get_imdb_dataset()
        if not dataset.is_dataset_available():
            def _show_downloading() -> None:
                """Surface the dataset-download message on the active progress dialog."""
                if isinstance(progress, xbmcgui.DialogProgressBG):
                    progress.update(0, heading, ADDON.getLocalizedString(32305))
                elif isinstance(progress, xbmcgui.DialogProgress):
                    progress.update(0, ADDON.getLocalizedString(32305))
            dataset.force_download(on_download_start=_show_downloading)

        stats = dataset.get_stats()
        dataset_date = str(stats.get("last_modified") or "")

        saved_progress = db.get_imdb_update_progress(media_type)
        if saved_progress:
            if saved_progress["dataset_date"] == dataset_date:
                processed_ids = saved_progress["processed_ids"]
                log(
                    "Ratings",
                    f"Resuming IMDb update for {media_type}: "
                    f"{len(processed_ids)}/{len(items)} already processed",
                )
            else:
                db.clear_imdb_update_progress(media_type)
                log("Ratings", f"New IMDb dataset detected, starting fresh for {media_type}")

    mdblist_fetcher: MdblistBatchFetcher | None = None
    if source_mode == "multi_source" and media_type in ("movie", "tvshow"):
        mdblist_fetcher = MdblistBatchFetcher(items, media_type)

    if media_type == "episode":
        ensure_episode_dataset(progress)
        prefetch_tvshow_uniqueids()

    monitor = xbmc.Monitor()

    with task_manager.TaskContext("Update Library Ratings") as ctx:
        if source_mode == "imdb":
            run_imdb_batch(
                media_type, items, progress, results, ctx, monitor, dataset_date, processed_ids
            )
        else:
            run_multi_source_batch(
                media_type, items, sources, progress, results, retry_queue, ctx, mdblist_fetcher
            )

    if progress:
        progress.close()

    if retry_queue and not use_background and not results.get("cancelled"):
        retry_count = prompt_and_process_retries(
            retry_queue, media_type, sources, source_mode
        )
        if retry_count > 0:
            results["retried"] = retry_count

    elapsed_time = time.time() - start_time
    results["elapsed_time"] = elapsed_time

    pending = results.get("pending_corrections", [])
    if pending and not use_background:
        results["imdb_ids_corrected"] = prompt_imdb_corrections(pending)
    elif pending:
        log(
            "Ratings",
            f"{len(pending)} IMDb ID redirects found but not corrected (background mode)",
            xbmc.LOGINFO,
        )

    results.pop("pending_corrections", None)

    db.save_operation_stats('ratings_update', results, scope=media_type)

    if not use_background:
        cancelled_text = " (Cancelled)" if results.get("cancelled") else ""
        imdb_ids_text = (
            f"\nIMDb IDs added: {results['imdb_ids_added']}"
            if results["imdb_ids_added"] > 0
            else ""
        )
        imdb_ids_corrected_text = (
            f"\nIMDb IDs corrected: {results['imdb_ids_corrected']}"
            if results["imdb_ids_corrected"] > 0
            else ""
        )
        message = (
            f"Updated: {results['updated']}\n"
            f"Failed: {results['failed']}\n"
            f"Skipped: {results['skipped']}{cancelled_text}{imdb_ids_text}{imdb_ids_corrected_text}"
        )
        show_ok(ADDON.getLocalizedString(32317), message)

    xbmc.executebuiltin("Container.Refresh")

    return results

