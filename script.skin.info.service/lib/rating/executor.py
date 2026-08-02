"""Batch executor for parallel ratings fetching with thread management."""
from __future__ import annotations

import time
import threading
from concurrent.futures import (
    ThreadPoolExecutor, as_completed, Future, TimeoutError as FuturesTimeoutError
)
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
import xbmc

from lib.kodi.client import log
from lib.data.api.client import RateLimitHit, RetryableError


MAX_WORKERS = 6
MAX_PER_SOURCE = 2
ITEM_TIMEOUT = 30.0
POLL_INTERVAL = 1.0


@dataclass
class FetchJob:
    """Represents a single fetch job for tracking."""
    item_dbid: int
    source_name: str
    future: Future
    submitted_at: float = field(default_factory=time.time)


@dataclass
class ItemState:
    """Tracks state for a single item being processed."""
    dbid: int
    title: str
    year: str
    media_type: str
    item: Dict
    existing_ratings: Dict
    ids: Dict
    pending_sources: Set[str] = field(default_factory=set)
    submitted_sources: Set[str] = field(default_factory=set)
    completed_sources: Set[str] = field(default_factory=set)
    deferred_sources: Set[str] = field(default_factory=set)
    ratings: List[Dict] = field(default_factory=list)
    sources_used: List[str] = field(default_factory=list)
    retryable_failures: List[Dict] = field(default_factory=list)
    _failed_source_set: Set[str] = field(default_factory=set)
    submitted_at: float = field(default_factory=time.time)
    finalized: bool = False


@dataclass
class RetryPoolEntry:
    """An item finalized with partial results, awaiting retry of missing sources."""
    dbid: int
    item: Dict
    title: str
    year: str
    media_type: str
    ids: Dict
    applied_ratings: Dict[str, Dict[str, float]]
    sources_used: List[str]
    missing_sources: Set[str]
    failures: List[Dict]


class RatingBatchExecutor:
    """Parallel rating fetcher with a 6-worker cap, 2-per-source cap, and pause-aware timeouts."""

    def __init__(self, sources: List, abort_flag=None):
        self.sources = sources
        self.source_names = {
            source: source.provider_name
            for source in sources
        }
        self.abort_flag = abort_flag

        self.executor: Optional[ThreadPoolExecutor] = None
        self.active_per_source: Dict[str, int] = {name: 0 for name in self.source_names.values()}
        self.pending_futures: Dict[Future, FetchJob] = {}
        self.item_states: Dict[int, ItemState] = {}

        self.source_paused_until: Dict[str, float] = {
            name: 0.0 for name in self.source_names.values()
        }

        self._lock = threading.Lock()
        self._cancelled = False

    def __enter__(self):
        self.executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        return self

    def __exit__(self, *_args):
        if self.executor:
            self.executor.shutdown(wait=False)
        return False

    def is_cancelled(self) -> bool:
        """Check if abort was requested."""
        if self._cancelled:
            return True
        if self.abort_flag and self.abort_flag.is_requested():
            self._cancelled = True
            return True
        return False

    def report_pause(self, source_name: str, until_ts: float) -> None:
        """Record a rate-limit wait and extend in-flight item timeouts by the wait duration.

        Without the extension, a pause that clears just before a worker's request
        returns can falsely time out a result that's about to arrive.
        """
        with self._lock:
            old_until = self.source_paused_until.get(source_name, 0.0)
            if until_ts <= old_until:
                return
            extension = until_ts - max(old_until, time.time())
            self.source_paused_until[source_name] = until_ts
            states_snapshot = list(self.item_states.values())

        if extension <= 0:
            return

        for state in states_snapshot:
            if state.finalized:
                continue
            waiting = state.submitted_sources | state.pending_sources
            if source_name in waiting:
                state.submitted_at += extension
            if source_name in state.pending_sources:
                state.pending_sources.discard(source_name)
                state.deferred_sources.add(source_name)

    def is_source_paused(self, source_name: str) -> bool:
        """True if `source_name` is currently in a rate-limit wait."""
        return time.time() < self.source_paused_until.get(source_name, 0.0)

    def submit_item(self, item: Dict, dbid: int, title: str, year: str,
                    media_type: str, ids: Dict, existing_ratings: Dict) -> None:
        """Submit fetch jobs for an item. Sources at capacity are queued until others complete.

        If a source is currently paused, the item's portion for that source is marked
        deferred immediately and will be retried later via the retry pool.
        """
        if self.is_cancelled() or not self.executor:
            return

        if dbid in self.item_states:
            log("Ratings",
                f"   WARNING: Item {dbid} ({title}) already submitted, skipping duplicate",
                xbmc.LOGWARNING)
            return

        state = ItemState(
            dbid=dbid,
            title=title,
            year=year,
            media_type=media_type,
            item=item,
            existing_ratings=existing_ratings,
            ids=ids
        )
        self.item_states[dbid] = state

        for source in self.sources:
            source_name = self.source_names[source]

            if self.is_source_paused(source_name):
                state.deferred_sources.add(source_name)
                continue

            if self.active_per_source[source_name] < MAX_PER_SOURCE:
                self._submit_job(state, source, source_name)
            else:
                state.pending_sources.add(source_name)

    def _submit_job(self, state: ItemState, source, source_name: str) -> None:
        """Submit a single fetch job to the executor."""
        if not self.executor:
            return

        if state.finalized:
            log("Ratings",
                f"   BUG: Trying to submit {source_name} for finalized item {state.title}",
                xbmc.LOGWARNING)
            return

        if source_name in state.submitted_sources:
            log("Ratings",
                f"   BUG: Trying to re-submit {source_name} for {state.title}",
                xbmc.LOGWARNING)
            return

        if source_name in state.completed_sources:
            log("Ratings",
                f"   BUG: Trying to submit {source_name} for {state.title} but already completed",
                xbmc.LOGWARNING)
            return

        state.submitted_sources.add(source_name)

        future = self.executor.submit(
            source.fetch_ratings,
            state.media_type,
            state.ids,
            self.abort_flag,
            False,
            self,
        )

        job = FetchJob(
            item_dbid=state.dbid,
            source_name=source_name,
            future=future
        )

        self.pending_futures[future] = job
        self.active_per_source[source_name] += 1

    def collect_results(self, timeout: float = POLL_INTERVAL) -> List[tuple[int, str, Any]]:
        """Return completed `(dbid, source_name, result_or_exception)` results, up to `timeout`."""
        if not self.pending_futures:
            return []

        results = []

        try:
            for future in as_completed(self.pending_futures.keys(), timeout=timeout):
                job = self.pending_futures.pop(future, None)
                if not job:
                    continue

                source_name = job.source_name
                dbid = job.item_dbid

                self.active_per_source[source_name] -= 1

                try:
                    ratings = future.result()
                    results.append((dbid, source_name, ratings))
                except RateLimitHit as e:
                    results.append((dbid, source_name, e))
                except RetryableError as e:
                    results.append((dbid, source_name, e))
                except Exception as e:
                    results.append((dbid, source_name, e))

        except FuturesTimeoutError:
            pass

        self._submit_pending_jobs()

        return results

    def _submit_pending_jobs(self) -> None:
        """Submit pending jobs for sources that now have capacity and are not paused."""
        if not self.executor:
            return

        for state in self.item_states.values():
            if state.finalized:
                continue

            pending_copy = set(state.pending_sources)
            for source_name in pending_copy:
                if self.is_source_paused(source_name):
                    state.pending_sources.discard(source_name)
                    state.deferred_sources.add(source_name)
                    continue
                if self.active_per_source[source_name] < MAX_PER_SOURCE:
                    source = self._get_source_by_name(source_name)
                    if source:
                        state.pending_sources.discard(source_name)
                        self._submit_job(state, source, source_name)

    def _get_source_by_name(self, name: str):
        """Get source instance by name."""
        for source, source_name in self.source_names.items():
            if source_name == name:
                return source
        return None

    def process_result(self, dbid: int, source_name: str, result: Any) -> None:
        """Update an item's state from one source's result."""
        state = self.item_states.get(dbid)
        if not state:
            log("Ratings",
                f"   {source_name}: Result for unknown item {dbid}, discarding",
                xbmc.LOGDEBUG)
            return

        if state.finalized:
            log("Ratings",
                f"   {source_name}: Late result for {state.title}, discarding",
                xbmc.LOGDEBUG)
            return

        state.completed_sources.add(source_name)

        if isinstance(result, RateLimitHit):
            wait = result.retry_after_seconds if result.retry_after_seconds else 60.0
            self.report_pause(source_name, time.time() + wait)
            state.completed_sources.discard(source_name)
            state.deferred_sources.add(source_name)
            log("Ratings", f"   {source_name}: 429 from server, pausing {wait:.1f}s", xbmc.LOGDEBUG)

        elif isinstance(result, RetryableError):
            log("Ratings", f"   {source_name}: Retryable error: {result.reason}", xbmc.LOGDEBUG)
            self._record_failure(state, source_name, result.reason)

        elif isinstance(result, Exception):
            log("Ratings", f"   {source_name}: Failed: {str(result)}", xbmc.LOGDEBUG)

        elif result:
            state.ratings.append(result)
            state.sources_used.append(source_name)

    def _record_failure(self, state: ItemState, source_name: str, reason: str) -> None:
        """Append a retryable failure entry, deduplicated by source."""
        if source_name in state._failed_source_set:
            return
        state._failed_source_set.add(source_name)
        state.retryable_failures.append({"source": source_name, "reason": reason})

    def check_item_timeout(self, dbid: int) -> bool:
        """True if the item has been in-flight longer than `ITEM_TIMEOUT`
        (pause-adjusted) and isn't finalized.

        Time spent waiting on currently-paused sources doesn't count toward the deadline.
        """
        state = self.item_states.get(dbid)
        if not state or state.finalized:
            return False

        # If any source we're still waiting on is currently paused, don't time out.
        waiting_on = (state.submitted_sources | state.pending_sources) - state.completed_sources
        for src in waiting_on:
            if self.is_source_paused(src):
                return False

        elapsed = time.time() - state.submitted_at
        return elapsed > ITEM_TIMEOUT

    def get_item_state(self, dbid: int) -> Optional[ItemState]:
        """Get the current state of an item."""
        return self.item_states.get(dbid)

    def mark_item_finalized(self, dbid: int) -> None:
        """Mark an item as finalized (ratings applied to Kodi)."""
        state = self.item_states.get(dbid)
        if state:
            log("Ratings",
                f"   Finalizing {state.title}: completed={state.completed_sources}, "
                f"deferred={state.deferred_sources}",
                xbmc.LOGDEBUG)
            state.finalized = True

    def get_unfinalized_items(self) -> List[int]:
        """Get list of item dbids that haven't been finalized."""
        return [
            dbid for dbid, state in self.item_states.items()
            if not state.finalized
        ]

    def timeout_pending_sources(self, dbid: int) -> None:
        """Mark all incomplete sources for a timed-out item as failed (deduplicated)."""
        state = self.item_states.get(dbid)
        if not state:
            return

        all_source_names = set(self.source_names.values())
        incomplete = all_source_names - state.completed_sources

        for source_name in incomplete:
            self._record_failure(state, source_name, "timeout")
            log("Ratings", f"   {source_name}: Timeout for {state.title}", xbmc.LOGDEBUG)

