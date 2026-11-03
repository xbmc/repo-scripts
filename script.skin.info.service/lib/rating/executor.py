"""Batch executor for parallel ratings fetching with thread management."""
from __future__ import annotations

import random
import time
import threading
from concurrent.futures import (
    ThreadPoolExecutor, as_completed, Future, TimeoutError as FuturesTimeoutError
)
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Final
import xbmc

from lib.kodi.client import log
from lib.data.api.client import RateLimitHit, RetryableError
from lib.data.api.source import RatingSource
from lib.infrastructure.tasks import MAX_REQUEST_SECONDS


MAX_WORKERS: Final = 8
MAX_PER_SOURCE: Final = 2
POLL_INTERVAL: Final = 1.0
# jittered so two sources pausing together do not resync
SHORT_HOLD = (2.0, 5.0)
MAX_REFUSALS: Final = 3
MAX_CONSECUTIVE_FAILURES: Final = 8
# backstops a stalled TLS handshake, which the watcher cannot kill
JOB_ABANDON_AFTER = MAX_REQUEST_SECONDS + 2.0

MAX_SOURCE_BACKLOG: Final = 15


@dataclass
class FetchJob:
    """One source's in-flight fetch for one item."""
    item_dbid: int
    source_name: str
    future: Future
    submitted_at: float = field(default_factory=time.time)


@dataclass
class ItemState:
    """One item's progress through its sources, and the ratings gathered so far."""
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


@dataclass
class RetryPoolEntry:
    """An item finalized with partial results, awaiting retry of missing sources."""
    dbid: int
    title: str
    year: str
    media_type: str
    ids: Dict
    applied_ratings: Dict[str, Dict[str, float]]
    sources_used: List[str]
    missing_sources: Set[str]
    failures: List[Dict]


class RatingBatchExecutor:
    """Parallel rating fetcher with a worker cap, a per-source cap, and admission backpressure."""

    def __init__(self, sources: List[RatingSource], abort_flag=None):
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
        self._monitor = xbmc.Monitor()
        self._refusals: Dict[str, int] = {}
        self._consecutive_failures: Dict[str, int] = {}
        self._spent_sources: Set[str] = set()
        self._abandoned: Dict[Future, str] = {}

    def __enter__(self):
        self.executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        return self

    def __exit__(self, *_args):
        if self.executor:
            self.executor.shutdown(wait=False)
        return False

    def is_cancelled(self) -> bool:
        """True once the run's abort flag fires; it stays true for the rest of the run."""
        if self._cancelled:
            return True
        if self.abort_flag and self.abort_flag.is_requested():
            self._cancelled = True
            return True
        return False

    def report_pause(self, source_name: str, until_ts: float) -> None:
        """Record a rate-limit pause; only a long one hands the source to the retry pool."""
        with self._lock:
            if until_ts <= self.source_paused_until.get(source_name, 0.0):
                return
            self.source_paused_until[source_name] = until_ts
            defer = until_ts - time.time() > SHORT_HOLD[1]
            states_snapshot = list(self.item_states.values())

        if not defer:
            return

        for state in states_snapshot:
            if source_name in state.pending_sources:
                state.pending_sources.discard(source_name)
                state.deferred_sources.add(source_name)

    def is_source_paused(self, source_name: str) -> bool:
        """True if the source is currently in a rate-limit wait."""
        return time.time() < self.source_paused_until.get(source_name, 0.0)

    def _spend_source(self, source_name: str) -> None:
        """Drop a source for the rest of the run, handing its queued items to the retry pool."""
        with self._lock:
            self._spent_sources.add(source_name)
            states = list(self.item_states.values())

        for state in states:
            if source_name in state.pending_sources:
                state.pending_sources.discard(source_name)
                state.deferred_sources.add(source_name)

    def _pause_outlasts_run(self, source_name: str) -> bool:
        """True once the source is spent for this run: long pause, repeated 429s, or failures."""
        if source_name in self._spent_sources:
            return True
        if self._refusals.get(source_name, 0) >= MAX_REFUSALS:
            return True
        if self._consecutive_failures.get(source_name, 0) >= MAX_CONSECUTIVE_FAILURES:
            return True
        return self.source_paused_until.get(source_name, 0.0) - time.time() > SHORT_HOLD[1]

    def submit_item(self, item: Dict, dbid: int, title: str, year: str,
                    media_type: str, ids: Dict, existing_ratings: Dict) -> None:
        """Submit fetch jobs; a busy or briefly paused source queues, a long-paused one defers."""
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

            # not deferred: a source that cannot serve this type is never coming back for it
            if not source.supports(media_type):
                continue

            if self._pause_outlasts_run(source_name):
                state.deferred_sources.add(source_name)
                continue

            if self.is_source_paused(source_name):
                state.pending_sources.add(source_name)
                continue

            if self.active_per_source[source_name] < MAX_PER_SOURCE:
                self._submit_job(state, source, source_name)
            else:
                state.pending_sources.add(source_name)

    def _submit_job(self, state: ItemState, source, source_name: str) -> None:
        """Submit a single fetch job to the executor."""
        if not self.executor:
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
        )

        job = FetchJob(
            item_dbid=state.dbid,
            source_name=source_name,
            future=future
        )

        self.pending_futures[future] = job
        self.active_per_source[source_name] += 1

    def _reclaim_finished_abandons(self) -> None:
        """Release the slot of an abandoned fetch once its thread finally dies."""
        for future, source_name in list(self._abandoned.items()):
            if future.done():
                del self._abandoned[future]
                self.active_per_source[source_name] -= 1

    def _abandon_overdue_jobs(self) -> List[tuple[int, str, Any]]:
        """Give up on a fetch the watcher could not kill; the thread runs on regardless."""
        self._reclaim_finished_abandons()
        now = time.time()
        abandoned = []
        for future, job in list(self.pending_futures.items()):
            if now - job.submitted_at <= JOB_ABANDON_AFTER:
                continue
            self.pending_futures.pop(future, None)
            self._abandoned[future] = job.source_name
            log("Ratings",
                f"   {job.source_name}: abandoned after {now - job.submitted_at:.1f}s "
                f"(dbid {job.item_dbid})",
                xbmc.LOGDEBUG)
            abandoned.append((job.item_dbid, job.source_name,
                              RetryableError(job.source_name, "no response")))
        return abandoned

    def collect_results(self, timeout: float = POLL_INTERVAL) -> List[tuple[int, str, Any]]:
        """Completed `(dbid, source_name, result_or_exception)` results collected this poll."""
        self._submit_pending_jobs()

        overdue = self._abandon_overdue_jobs()
        if overdue:
            return overdue

        if not self.pending_futures:
            if timeout > 0 and self._has_queued_work():
                self._monitor.waitForAbort(timeout)
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

    def _has_queued_work(self) -> bool:
        """True if some item is still queued behind a source."""
        return any(state.pending_sources for state in self.item_states.values())

    def _submit_pending_jobs(self) -> None:
        """Submit pending jobs for sources that now have capacity and are not paused."""
        if not self.executor:
            return

        for state in list(self.item_states.values()):
            pending_copy = set(state.pending_sources)
            for source_name in pending_copy:
                if self._pause_outlasts_run(source_name):
                    state.pending_sources.discard(source_name)
                    state.deferred_sources.add(source_name)
                    continue

                if self.is_source_paused(source_name):
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
                f"   {source_name}: Result for item {dbid} no longer tracked, discarding",
                xbmc.LOGDEBUG)
            return

        state.completed_sources.add(source_name)

        if isinstance(result, RateLimitHit):
            named = result.retry_after_seconds
            state.completed_sources.discard(source_name)
            state.submitted_sources.discard(source_name)
            hits = self._refusals.get(source_name, 0) + 1
            self._refusals[source_name] = hits

            if (named is not None and named <= SHORT_HOLD[1]
                    and hits < MAX_REFUSALS):
                hold = max(named, random.uniform(*SHORT_HOLD))
                self.report_pause(source_name, time.time() + hold)
                state.pending_sources.add(source_name)
                log("Ratings", f"   {source_name}: 429, holding {hold:.1f}s", xbmc.LOGDEBUG)
                return

            if named:
                self.report_pause(source_name, time.time() + named)
            self._spend_source(source_name)
            state.deferred_sources.add(source_name)
            log("Ratings",
                f"   {source_name}: 429 with no ridable wait, dropped for this run",
                xbmc.LOGDEBUG)
            return

        # only a refusal moves the 429 count; a result may be cache-served, which proves nothing
        if isinstance(result, Exception):
            reason = result.reason if isinstance(result, RetryableError) else str(result)
            log("Ratings", f"   {source_name}: Failed: {reason}", xbmc.LOGDEBUG)
            self._record_failure(state, source_name, reason)
            fails = self._consecutive_failures.get(source_name, 0) + 1
            self._consecutive_failures[source_name] = fails
            if fails == MAX_CONSECUTIVE_FAILURES:
                log("Ratings",
                    f"   {source_name}: {fails} failures in a row, dropped for this run",
                    xbmc.LOGINFO)
            return

        self._consecutive_failures[source_name] = 0

        if result:
            state.ratings.append(result)
            state.sources_used.append(source_name)

    def _record_failure(self, state: ItemState, source_name: str, reason: str) -> None:
        """Append a retryable failure entry, deduplicated by source."""
        if source_name in state._failed_source_set:
            return
        state._failed_source_set.add(source_name)
        state.retryable_failures.append({"source": source_name, "reason": reason})

    def source_backlog(self) -> Dict[str, int]:
        """Unfinished item count owed by each source."""
        with self._lock:
            states = list(self.item_states.values())
        counts: Dict[str, int] = {}
        for state in states:
            outstanding = (
                (state.submitted_sources | state.pending_sources)
                - state.completed_sources
                - state.deferred_sources
            )
            for source_name in outstanding:
                counts[source_name] = counts.get(source_name, 0) + 1
        return counts

    def max_source_backlog(self) -> int:
        """Largest unfinished item count owed by any single source."""
        counts = self.source_backlog()
        return max(counts.values()) if counts else 0

    def pause_remaining(self, source_name: str) -> int:
        """Seconds left on a source's rate-limit hold."""
        with self._lock:
            until = self.source_paused_until.get(source_name, 0.0)
        return max(0, int(until - time.time()))

    def get_item_state(self, dbid: int) -> Optional[ItemState]:
        """Get an item's tracked state, or None once it is finalized."""
        return self.item_states.get(dbid)

    def mark_item_finalized(self, dbid: int) -> None:
        """Drop a finished item; scans iterate every tracked state."""
        state = self.item_states.pop(dbid, None)
        if state:
            log("Ratings",
                f"   Finalizing {state.title}: completed={state.completed_sources}, "
                f"deferred={state.deferred_sources}",
                xbmc.LOGDEBUG)

    def paused_sources(self) -> List[str]:
        """Names of sources currently inside a rate-limit hold."""
        with self._lock:
            snapshot = list(self.source_paused_until.items())
        now = time.time()
        return sorted(name for name, until in snapshot if until > now)

    def all_sources_spent(self) -> bool:
        """True when every source is spent for this run."""
        names = list(self.active_per_source)
        return bool(names) and all(self._pause_outlasts_run(n) for n in names)

    def get_unfinalized_items(self) -> List[int]:
        """Dbids still being worked; a finalized item is removed outright."""
        return list(self.item_states)
