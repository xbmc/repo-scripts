"""Multi-source batch ratings: parallel executor driver, MDBList batch fetcher, per-item helpers."""
from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

import xbmc
import xbmcgui

from lib.infrastructure import tasks as task_manager
from lib.kodi.client import get_api_key, format_item_label, log, ADDON
from lib.data.api.tmdb import ApiTmdb, resolve_tmdb_id
from lib.data.api.mdblist import (
    ApiMdblist as MDBListRatingsSource,
    BATCH_SIZE as MDBLIST_BATCH_SIZE,
)
from lib.data.api.client import RateLimitHit, RetryableError
from lib.data.database.rating import cached_provider_keys
from lib.rating.executor import (
    RatingBatchExecutor, ItemState, RetryPoolEntry, MAX_SOURCE_BACKLOG,
)
from lib.rating.ids import get_tvshow_uniqueid
from lib.rating.single import (
    resolve_item_ids,
    get_imdb_dataset_rating,
    merge_and_apply_ratings,
)


def count_trakt_requests(media_type: str, items: List[Dict]) -> int:
    """Requests a Trakt pass would make; an episode season costs one call, not one per episode."""
    cached = cached_provider_keys("trakt", media_type)

    if media_type == "episode":
        seasons: Set[Tuple[str, int]] = set()
        for item in items:
            show_imdb = (get_tvshow_uniqueid(item.get("tvshowid", 0)) or {}).get("imdb")
            season = item.get("season")
            if not show_imdb or season is None:
                continue
            if (show_imdb, int(season), int(item.get("episode") or -1)) not in cached:
                seasons.add((show_imdb, int(season)))
        return len(seasons)

    pending = 0
    for item in items:
        imdb_id = item.get("uniqueid", {}).get("imdb")
        if imdb_id and (imdb_id, -1, -1) not in cached:
            pending += 1
    return pending


def normalize_existing_ratings(existing_ratings: Dict) -> Dict[str, Dict[str, float]]:
    """Convert Kodi-shaped existing ratings into the merge-baseline format."""
    return {
        name: {"rating": d.get("rating", 0), "votes": float(d.get("votes", 0))}
        for name, d in existing_ratings.items()
        if isinstance(d, dict) and d.get("rating") is not None
    }


def build_retry_entry(state: ItemState, item_stats: Optional[Dict]) -> Optional[RetryPoolEntry]:
    """Build a retry entry for the sources an item still lacks, based on what Kodi now holds."""
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

    title = format_item_label(item, media_type) or "Unknown"
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


def render_progress(
    progress: xbmcgui.DialogProgress | xbmcgui.DialogProgressBG,
    finalized: int,
    total: int,
    detail: str,
) -> None:
    """Update the modal or background progress dialog."""
    percent = int((finalized / total) * 100) if total else 0
    if isinstance(progress, xbmcgui.DialogProgressBG):
        progress.update(percent, ADDON.getLocalizedString(32300),
                        ADDON.getLocalizedString(32306).format(finalized, total, detail))
    elif isinstance(progress, xbmcgui.DialogProgress):
        progress.update(
            percent,
            f"{ADDON.getLocalizedString(32307).format(finalized, total)}\n{detail}")


def report_source_wait(
    progress: xbmcgui.DialogProgress | xbmcgui.DialogProgressBG,
    executor: RatingBatchExecutor,
    finalized: int,
    total: int,
    title: str,
) -> None:
    """Update the dialog while work is in flight, naming a rate-limited source if there is one."""
    paused = executor.paused_sources()
    if paused:
        seconds = max((executor.pause_remaining(name) for name in paused), default=0)
        title = ADDON.getLocalizedString(32321).format(", ".join(paused), seconds)
    render_progress(progress, finalized, total, title)


class TmdbSeasonFetcher:
    """Just-in-time TMDB season fetcher; caches a show's episode ratings by season."""

    def __init__(self, items: List[Dict]):
        self.tmdb = ApiTmdb()
        self.seasons: Dict[str, Set[int]] = {}
        self._fetched: Set[str] = set()

        for item in items:
            show_dbid = item.get("tvshowid")
            season = item.get("season")
            if not show_dbid or season is None:
                continue
            tmdb_id = (get_tvshow_uniqueid(show_dbid) or {}).get("tmdb")
            if tmdb_id:
                self.seasons.setdefault(str(tmdb_id), set()).add(int(season))

    def prefetch_for_show(self, ids: Dict, abort_flag=None) -> None:
        """Cache a show's episode ratings when its first episode comes up."""
        tmdb_id = str(ids.get("tmdb") or "")
        if not tmdb_id or tmdb_id in self._fetched:
            return
        self._fetched.add(tmdb_id)

        seasons = self.seasons.get(tmdb_id)
        if not seasons:
            return

        try:
            stored = self.tmdb.prefetch_episode_ratings(
                int(tmdb_id), sorted(seasons), abort_flag)
        except (RateLimitHit, RetryableError) as e:
            log("Ratings", f"TMDB: episode prefetch failed for show {tmdb_id}: {e}",
                xbmc.LOGDEBUG)
            return

        log("Ratings",
            f"TMDB: cached {stored} episode ratings for show {tmdb_id} "
            f"({len(seasons)} season(s))",
            xbmc.LOGDEBUG)


class MdblistBatchFetcher:
    """Just-in-time MDBList fetcher: one batch per `BATCH_SIZE` items, into the cache items read."""

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
        abort_flag=None,
    ) -> None:
        """Fetch the MDBList batch covering this item if at a batch boundary; no-op otherwise."""
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
            self.mdblist.fetch_batch(
                self.media_type, batch_ids, provider="tmdb", abort_flag=abort_flag)
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
    tmdb_fetcher: Optional[TmdbSeasonFetcher] = None,
) -> None:
    """Run a ratings pass, admitting items to the executor as its per-source backlog allows."""

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
            - check_state.deferred_sources
        )
        if in_flight:
            return finalized_count

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

            if executor.all_sources_spent():
                results["all_sources_down"] = True
                log("Ratings", "No source reachable, stopping the run", xbmc.LOGWARNING)
                break

            if mdblist_fetcher:
                mdblist_fetcher.fetch_batch_for_index(i, progress, ctx.abort_flag)

            prepared = prepare_item_for_batch(item, media_type)
            dbid, title, year, ids, existing_ratings, initial_ratings, initial_sources = prepared

            if dbid is None or title is None or ids is None or existing_ratings is None:
                results["skipped"] += 1
                continue

            if tmdb_fetcher:
                tmdb_fetcher.prefetch_for_show(ids, ctx.abort_flag)

            while executor.max_source_backlog() >= MAX_SOURCE_BACKLOG:
                if executor.is_cancelled():
                    break
                if isinstance(progress, xbmcgui.DialogProgress) and progress.iscanceled():
                    break
                ctx.mark_progress()
                report_source_wait(
                    progress, executor, items_finalized, len(items), title)
                for result_dbid, source_name, result in executor.collect_results(timeout=0.5):
                    executor.process_result(result_dbid, source_name, result)
                for check_dbid in executor.get_unfinalized_items():
                    items_finalized = _try_finalize(executor, check_dbid, items_finalized)

            if executor.is_cancelled() or (
                    isinstance(progress, xbmcgui.DialogProgress) and progress.iscanceled()):
                results["cancelled"] = True
                break

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

            render_progress(progress, items_finalized, len(items), title)

        while executor.get_unfinalized_items():
            if executor.is_cancelled():
                results["cancelled"] = True
                break

            if isinstance(progress, xbmcgui.DialogProgress) and progress.iscanceled():
                results["cancelled"] = True
                break

            ctx.mark_progress()
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
