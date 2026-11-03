"""Retry queue: targeted re-fetch of missing sources after a batch run, with user prompt."""
from __future__ import annotations

import time
from typing import Dict, List, Optional, Set

import xbmc
import xbmcgui

from lib.kodi.client import request, log, KODI_SET_DETAILS_METHODS, ADDON
from lib.kodi.settings import KodiSettings
from lib.data.api.client import RateLimitHit, RetryableError
from lib.data.api.source import RatingSource
from lib.data.database import workflow as db
from lib.infrastructure.tasks import ShutdownAbortFlag, MAX_REQUEST_SECONDS
from lib.infrastructure.dialogs import (
    show_textviewer, show_notification, show_yesnocustom, DialogProgress)
from lib.rating.merger import merge_ratings, prepare_kodi_ratings, rating_owner
from lib.rating.executor import (
    RetryPoolEntry, MAX_CONSECUTIVE_FAILURES, SHORT_HOLD,
)
from lib.rating.ids import build_external_ids


MAX_PAUSE_WAIT = SHORT_HOLD[1]


def _note_retry_failure(source_name: str, failures: Dict[str, int],
                        refused: Set[str]) -> None:
    """Count a source's consecutive retry failures, dropping it for the pass at the cap."""
    hits = failures.get(source_name, 0) + 1
    failures[source_name] = hits
    if hits == MAX_CONSECUTIVE_FAILURES:
        refused.add(source_name)
        log("Ratings",
            f"   {source_name}: {hits} retry failures in a row, dropped for this pass",
            xbmc.LOGINFO)


def _retry_replaces(name: str, fresh: Set[str], prior: Set[str],
                    votes: float, existing_votes: float) -> bool:
    """True when a retried rating beats the applied one: its owner first, then vote count."""
    owner = rating_owner(name)
    incoming_is_owner = owner is not None and owner in fresh
    existing_is_owner = owner is not None and owner in prior
    if incoming_is_owner != existing_is_owner:
        return incoming_is_owner
    return votes > existing_votes


def retry_targeted(entry: RetryPoolEntry, sources: List[RatingSource],
                   paused_until: Dict[str, float],
                   abort_flag=None, is_cancelled=None,
                   refused: Optional[Set[str]] = None,
                   waited_for: Optional[Set[str]] = None,
                   failures: Optional[Dict[str, int]] = None) -> bool:
    """Fetch one entry's missing sources and merge into Kodi; True if all resolved."""
    if refused is None:
        refused = set()
    if waited_for is None:
        waited_for = set()
    if failures is None:
        failures = {}
    target_sources = [
        s for s in sources
        if s.provider_name in entry.missing_sources
    ]
    if not target_sources:
        return True

    new_ratings: List[Dict] = []
    still_missing: Set[str] = set()
    prior_sources = set(entry.sources_used)

    for index, source in enumerate(target_sources):
        source_name = source.provider_name

        if source_name in refused:
            still_missing.add(source_name)
            continue

        remaining = paused_until.get(source_name, 0.0) - time.time()
        if remaining > 0:
            if remaining > MAX_PAUSE_WAIT or (
                    abort_flag and abort_flag.is_requested()):
                still_missing.add(source_name)
                continue
            monitor = xbmc.Monitor()
            waited = 0.0
            interrupted = False
            while waited < remaining:
                if monitor.waitForAbort(1.0) or (abort_flag and abort_flag.is_requested()):
                    interrupted = True
                    break
                if is_cancelled and is_cancelled():
                    interrupted = True
                    break
                waited += 1.0
            if interrupted:
                still_missing.update(
                    s.provider_name for s in target_sources[index:]
                )
                break

            waited_for.add(source_name)

        try:
            result = source.fetch_ratings(entry.media_type, entry.ids, abort_flag)
        except RateLimitHit as e:
            wait = e.retry_after_seconds
            if wait:
                paused_until[source_name] = time.time() + wait
            if not wait or source_name in waited_for:
                refused.add(source_name)
            still_missing.add(source_name)
            log("Ratings",
                f"   {source_name}: 429 in retry, "
                f"{f'deferring {wait:.1f}s' if wait else 'dropped for this pass'}",
                xbmc.LOGDEBUG)
            continue
        except RetryableError as e:
            still_missing.add(source_name)
            seen = {f.get("source") for f in entry.failures}
            if source_name not in seen:
                entry.failures.append({"source": source_name, "reason": e.reason})
            _note_retry_failure(source_name, failures, refused)
            continue
        except Exception as e:
            log("Ratings", f"   {source_name}: Retry failed: {e}", xbmc.LOGDEBUG)
            still_missing.add(source_name)
            _note_retry_failure(source_name, failures, refused)
            continue

        failures[source_name] = 0

        if result:
            new_ratings.append(result)
            entry.sources_used.append(source_name)
        else:
            still_missing.add(source_name)

    if not new_ratings:
        entry.missing_sources = still_missing
        return False

    merged_new = merge_ratings(new_ratings)
    fresh_sources = set(entry.sources_used) - prior_sources
    final_ratings = dict(entry.applied_ratings)
    for name, data in merged_new.items():
        new_val = data.get("rating")
        if new_val is None:
            continue
        new_votes = float(data.get("votes", 0))
        existing = final_ratings.get(name)
        if existing is None or _retry_replaces(
                name, fresh_sources, prior_sources, new_votes, float(existing.get("votes", 0))):
            final_ratings[name] = {"rating": new_val, "votes": new_votes}

    method_info = KODI_SET_DETAILS_METHODS.get(entry.media_type)
    if not method_info:
        entry.missing_sources = still_missing
        return False
    method, id_key = method_info

    kodi_ratings = prepare_kodi_ratings(
        final_ratings, default_source=KodiSettings.ratings_default_source(),
        supplied=set(merged_new))
    response = request(method, {id_key: entry.dbid, "ratings": kodi_ratings})

    if response is None:
        entry.missing_sources = still_missing
        return False

    db.update_synced_ratings(
        entry.media_type, entry.dbid, final_ratings,
        build_external_ids(entry.ids, entry.media_type)
    )
    entry.applied_ratings = final_ratings
    entry.missing_sources = still_missing

    return not still_missing


def prompt_and_process_retries(retry_queue: List[RetryPoolEntry], sources: List) -> int:
    """Prompt user to retry items with missing/failed sources; reprocess if confirmed."""
    count = len(retry_queue)

    failure_summary: Dict[str, int] = {}
    for entry in retry_queue:
        for source in entry.missing_sources:
            failure_summary[source] = failure_summary.get(source, 0) + 1

    summary_parts = [f"{source}: {cnt}" for source, cnt in sorted(failure_summary.items())]
    summary_text = ", ".join(summary_parts)

    message = (
        f"{ADDON.getLocalizedString(32416).format(count)}\n"
        f"({summary_text})\n\n"
        f"{ADDON.getLocalizedString(32417)}"
    )

    while True:
        result = show_yesnocustom(
            ADDON.getLocalizedString(32415),
            message,
            customlabel=ADDON.getLocalizedString(32427),
            nolabel=ADDON.getLocalizedString(32128),
            yeslabel=ADDON.getLocalizedString(32429)
        )

        if result == 2:
            lines = [f"[B]{ADDON.getLocalizedString(32419)}[/B]", ""]
            for entry in retry_queue:
                year_str = f" ({entry.year})" if entry.year else ""
                lines.append(f"{entry.title}{year_str}")

                for source in sorted(entry.missing_sources):
                    reason = next(
                        (f.get("reason") for f in entry.failures if f.get("source") == source),
                        "deferred (rate limit)"
                    )
                    lines.append(f"  {source}: {reason}")
                lines.append("")

            show_textviewer(ADDON.getLocalizedString(32418), "\n".join(lines))

        elif result == 1:
            return _process_retry_queue(retry_queue, sources)

        else:
            log("Ratings",
                f"User skipped retry of {count} item{'s' if count > 1 else ''}",
                xbmc.LOGINFO)
            return 0


def _process_retry_queue(retry_queue: List[RetryPoolEntry], sources: List) -> int:
    """Process the retry queue, fetching only the missing sources; returns how many resolved."""
    progress = DialogProgress()
    progress.create(ADDON.getLocalizedString(32300), ADDON.getLocalizedString(32310))

    success_count = 0
    total = len(retry_queue)
    paused_until: Dict[str, float] = {}
    refused: Set[str] = set()
    waited_for: Set[str] = set()
    failures: Dict[str, int] = {}
    abort_flag = ShutdownAbortFlag(MAX_REQUEST_SECONDS)

    for i, entry in enumerate(retry_queue):
        if progress.iscanceled():
            break

        percent = int((i / max(total, 1)) * 100)
        progress.update(
            percent,
            f"{ADDON.getLocalizedString(32311).format(i+1, total)}\n{entry.title}"
        )

        success = retry_targeted(
            entry, sources, paused_until, abort_flag=abort_flag,
            is_cancelled=progress.iscanceled, refused=refused,
            waited_for=waited_for, failures=failures)

        if success:
            success_count += 1
            log("Ratings", f"Retry succeeded: {entry.title}", xbmc.LOGDEBUG)
        else:
            log("Ratings",
                f"Retry failed: {entry.title} (still missing: {entry.missing_sources})",
                xbmc.LOGDEBUG)

    progress.close()

    if success_count > 0:
        show_notification(
            ADDON.getLocalizedString(32300),
            ADDON.getLocalizedString(32420).format(success_count, total),
            xbmcgui.NOTIFICATION_INFO,
            3000
        )

    return success_count
