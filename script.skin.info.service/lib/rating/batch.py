"""Multi-source batch ratings: parallel executor driver, MDBList batch fetcher, per-item helpers."""
from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

import xbmc
import xbmcgui

from lib.infrastructure import tasks as task_manager
from lib.kodi.client import get_api_key, log, ADDON
from lib.data.api.tmdb import resolve_tmdb_id
from lib.data.api.mdblist import (
    ApiMdblist as MDBListRatingsSource,
    BATCH_SIZE as MDBLIST_BATCH_SIZE,
)
from lib.data.api.client import RateLimitHit
from lib.rating.executor import RatingBatchExecutor, ItemState, RetryPoolEntry
from lib.rating.single import (
    resolve_item_ids,
    get_imdb_dataset_rating,
    merge_and_apply_ratings,
)


def normalize_existing_ratings(existing_ratings: Dict) -> Dict[str, Dict[str, float]]:
    """Convert Kodi-shaped existing ratings into the merge-baseline format."""
    return {
        name: {"rating": d.get("rating", 0), "votes": float(d.get("votes", 0))}
        for name, d in existing_ratings.items()
        if isinstance(d, dict) and d.get("rating") is not None
    }


def build_retry_entry(state: ItemState, item_stats: Optional[Dict]) -> Optional[RetryPoolEntry]:
    """Build a retry entry for items that finished with deferred or failed sources.

    `applied_ratings` is the merge baseline for retry: either what we wrote to Kodi
    on first apply, or the existing Kodi state if no write happened.
    """
    failure_sources: Set[str] = {
        s for s in (f.get("source") for f in state.retryable_failures) if s
    }
    missing = state.deferred_sources | failure_sources
    if not missing:
        return None

    if item_stats and item_stats.get("final_ratings"):
        baseline = item_stats["final_ratings"]
    else:
        baseline = normalize_existing_ratings(state.existing_ratings)

    return RetryPoolEntry(
        dbid=state.dbid,
        item=state.item,
        title=state.title,
        year=state.year,
        media_type=state.media_type,
        ids=state.ids,
        applied_ratings=baseline,
        sources_used=list(state.sources_used),
        missing_sources=missing,
        failures=list(state.retryable_failures),
    )


def prepare_item_for_batch(
    item: Dict,
    media_type: str,
) -> Tuple[
    Optional[int], Optional[str], Optional[str], Optional[Dict], Optional[Dict],
    Optional[List[Dict]], Optional[List[str]],
]:
    """Prepare an item for batch processing by extracting IDs and fetching IMDb dataset rating."""
    dbid = item.get("movieid") or item.get("episodeid") or item.get("tvshowid")
    if not dbid:
        return None, None, None, None, None, None, None

    title = item.get("title", "Unknown")
    year = item.get("year", "")
    existing_ratings = item.get("ratings", {})

    ids = resolve_item_ids(item, media_type)
    if ids is None:
        return None, None, None, None, None, None, None

    initial_ratings, initial_sources = get_imdb_dataset_rating(ids, media_type)

    return (
        dbid, title, str(year) if year else "", ids, existing_ratings,
        initial_ratings, initial_sources,
    )


def finalize_item_ratings(
    state: ItemState,
    media_type: str,
) -> Tuple[Optional[bool], Optional[Dict]]:
    """Finalize ratings for an item by merging and applying to Kodi."""
    return merge_and_apply_ratings(
        media_type=media_type,
        dbid=state.dbid,
        title=state.title,
        year=state.year,
        all_ratings=state.ratings,
        sources_used=state.sources_used,
        existing_ratings=state.existing_ratings,
        ids=state.ids,
        retryable_failures=state.retryable_failures,
    )


class MdblistBatchFetcher:
    """Just-in-time MDBList batch fetcher.

    Fetches 200 items at a time at batch boundaries; data lands in SQLite cache for
    later per-item retrieval.
    """

    def __init__(self, items: List[Dict], media_type: str):
        self.media_type = media_type
        self.mdblist = MDBListRatingsSource() if get_api_key("mdblist_api_key") else None
        self.daily_limit_reached = False

        self.tmdb_ids: list[str] = []
        for item in items:
            uniqueid = item.get("uniqueid", {})
            raw_tmdb = uniqueid.get("tmdb")
            imdb_id = uniqueid.get("imdb")
            resolved = resolve_tmdb_id(str(raw_tmdb) if raw_tmdb else None, imdb_id, media_type)
            self.tmdb_ids.append(resolved or "")

        self.total_items = len(self.tmdb_ids)

    def fetch_batch_for_index(
        self,
        index: int,
        progress: xbmcgui.DialogProgress | xbmcgui.DialogProgressBG | None = None,
    ) -> None:
        """Fetch the MDBList batch covering `index` if at a batch boundary; no-op otherwise."""
        if not self.mdblist or self.daily_limit_reached:
            return

        if self.media_type == "episode":
            return

        if index % MDBLIST_BATCH_SIZE != 0:
            return

        batch_start = index
        batch_end = min(index + MDBLIST_BATCH_SIZE, self.total_items)

        batch_ids = [
            {"id": tmdb_id}
            for tmdb_id in self.tmdb_ids[batch_start:batch_end]
            if tmdb_id
        ]

        if not batch_ids:
            return

        batch_num = (index // MDBLIST_BATCH_SIZE) + 1
        total_batches = (self.total_items + MDBLIST_BATCH_SIZE - 1) // MDBLIST_BATCH_SIZE

        log(
            "Ratings",
            f"Fetching MDBList batch {batch_num}/{total_batches} ({len(batch_ids)} items)",
            xbmc.LOGDEBUG,
        )

        if progress:
            if isinstance(progress, xbmcgui.DialogProgressBG):
                progress.update(
                    int((index / self.total_items) * 100),
                    ADDON.getLocalizedString(32300),
                    ADDON.getLocalizedString(32414).format(batch_num, total_batches)
                )
            elif isinstance(progress, xbmcgui.DialogProgress):
                progress.update(
                    int((index / self.total_items) * 100),
                    ADDON.getLocalizedString(32414).format(batch_num, total_batches)
                )

        try:
            self.mdblist.fetch_batch(self.media_type, batch_ids, provider="tmdb")
        except RateLimitHit:
            log("Ratings", "MDBList daily limit reached", xbmc.LOGWARNING)
            self.daily_limit_reached = True


def run_multi_source_batch(
    media_type: str,
    items: List[Dict],
    sources: List,
    progress: xbmcgui.DialogProgress | xbmcgui.DialogProgressBG,
    results: Dict,
    retry_queue: List[RetryPoolEntry],
    ctx: task_manager.TaskContext,
    mdblist_fetcher: Optional[MdblistBatchFetcher],
) -> None:
    """Run multi-source batch update via `RatingBatchExecutor`.

    Items finishing with deferred or failed sources are appended to `retry_queue`
    as `RetryPoolEntry` objects for later user-confirmed targeted retry.
    """

    def _collect_result(success: Optional[bool], item_stats: Optional[Dict]) -> None:
        if success:
            results["updated"] += 1
        elif success is None:
            results["skipped"] += 1
        else:
            results["failed"] += 1

        if not item_stats:
            return

        results["total_ratings_added"] += item_stats.get("ratings_added", 0)
        results["total_ratings_updated"] += item_stats.get("ratings_updated", 0)
        if item_stats.get("imdb_id_added"):
            results["imdb_ids_added"] += 1
        if item_stats.get("pending_correction"):
            results["pending_corrections"].append(item_stats["pending_correction"])

        for source_name in item_stats.get("sources_used", []):
            if source_name not in results["source_stats"]:
                results["source_stats"][source_name] = {"fetched": 0, "failed": 0}
            results["source_stats"][source_name]["fetched"] += 1

        if item_stats.get("ratings_added", 0) > 0 or item_stats.get("ratings_updated", 0) > 0:
            results["item_details"].append(item_stats)
            if len(results["item_details"]) > 20:
                results["item_details"].pop(0)

    def _try_finalize(executor: RatingBatchExecutor, check_dbid: int, finalized_count: int) -> int:
        check_state = executor.get_item_state(check_dbid)
        if not check_state:
            return finalized_count

        in_flight = (
            (check_state.submitted_sources | check_state.pending_sources)
            - check_state.completed_sources
        )
        all_sources_done = not in_flight
        timed_out = executor.check_item_timeout(check_dbid)

        if not all_sources_done and not timed_out:
            return finalized_count

        if timed_out and not all_sources_done:
            executor.timeout_pending_sources(check_dbid)

        success, item_stats = finalize_item_ratings(check_state, media_type)
        retry_entry = build_retry_entry(check_state, item_stats)
        executor.mark_item_finalized(check_dbid)
        _collect_result(success, item_stats)

        if retry_entry is not None:
            retry_queue.append(retry_entry)

        ctx.mark_progress()
        return finalized_count + 1

    with RatingBatchExecutor(sources, ctx.abort_flag) as executor:
        items_finalized = 0

        for i, item in enumerate(items):
            if executor.is_cancelled():
                results["cancelled"] = True
                break

            if isinstance(progress, xbmcgui.DialogProgress) and progress.iscanceled():
                results["cancelled"] = True
                break

            if mdblist_fetcher:
                mdblist_fetcher.fetch_batch_for_index(i, progress)

            prepared = prepare_item_for_batch(item, media_type)
            dbid, title, year, ids, existing_ratings, initial_ratings, initial_sources = prepared

            if dbid is None or title is None or ids is None or existing_ratings is None:
                results["skipped"] += 1
                continue

            executor.submit_item(
                item=item, dbid=dbid, title=title, year=year or "",
                media_type=media_type, ids=ids, existing_ratings=existing_ratings,
            )

            state = executor.get_item_state(dbid)
            if state and initial_ratings and initial_sources:
                state.ratings.extend(initial_ratings)
                state.sources_used.extend(initial_sources)

            collected = executor.collect_results(timeout=0.1)
            for result_dbid, source_name, result in collected:
                executor.process_result(result_dbid, source_name, result)

            for check_dbid in executor.get_unfinalized_items():
                items_finalized = _try_finalize(executor, check_dbid, items_finalized)

            # Percent reflects finalized items, never submission index, otherwise the bar
            # races to 100% during fast submission and then snaps back when the drain loop
            # starts reporting actual completion.
            percent = int((items_finalized / len(items)) * 100)
            if isinstance(progress, xbmcgui.DialogProgressBG):
                progress.update(
                    percent,
                    ADDON.getLocalizedString(32300),
                    ADDON.getLocalizedString(32306).format(i+1, len(items), title),
                )
            elif isinstance(progress, xbmcgui.DialogProgress):
                progress.update(
                    percent,
                    f"{ADDON.getLocalizedString(32307).format(i+1, len(items))}\n{title}",
                )

        while executor.get_unfinalized_items():
            if executor.is_cancelled():
                results["cancelled"] = True
                break

            if isinstance(progress, xbmcgui.DialogProgress) and progress.iscanceled():
                results["cancelled"] = True
                break

            collected = executor.collect_results(timeout=1.0)
            for result_dbid, source_name, result in collected:
                executor.process_result(result_dbid, source_name, result)

            for check_dbid in executor.get_unfinalized_items():
                items_finalized = _try_finalize(executor, check_dbid, items_finalized)

                percent = int((items_finalized / len(items)) * 100)
                if isinstance(progress, xbmcgui.DialogProgressBG):
                    progress.update(
                        percent,
                        ADDON.getLocalizedString(32300),
                        ADDON.getLocalizedString(32308).format(items_finalized, len(items)),
                    )
                elif isinstance(progress, xbmcgui.DialogProgress):
                    progress.update(
                        percent,
                        ADDON.getLocalizedString(32309).format(items_finalized, len(items)),
                    )
