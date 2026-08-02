"""Retry queue: targeted re-fetch of missing sources after a batch run, with user prompt."""
from __future__ import annotations

import time
from typing import Dict, List, Set

import xbmc
import xbmcgui

from lib.kodi.client import request, log, KODI_SET_DETAILS_METHODS, ADDON
from lib.data.api.client import RateLimitHit, RetryableError
from lib.data.database import workflow as db
from lib.infrastructure.dialogs import (
    show_textviewer, show_notification, show_yesnocustom, DialogProgress)
from lib.rating.merger import merge_ratings, prepare_kodi_ratings
from lib.rating.executor import RetryPoolEntry
from lib.rating.ids import build_external_ids
from lib.rating.imdb import update_single_item_imdb


def retry_targeted(entry: RetryPoolEntry, sources: List, paused_until: Dict[str, float],
                   abort_flag=None) -> bool:
    """Fetch only the missing sources for one entry; merge into Kodi.

    Skips sources still inside their `paused_until` window (set by prior 429s in
    this retry pass). On 429, records a new pause and keeps the source in
    missing_sources for a subsequent pass. Returns True iff all missing resolved.
    """
    target_sources = [
        s for s in sources
        if s.provider_name in entry.missing_sources
    ]
    if not target_sources:
        return True

    new_ratings: List[Dict] = []
    still_missing: Set[str] = set()

    for source in target_sources:
        source_name = source.provider_name

        if time.time() < paused_until.get(source_name, 0.0):
            still_missing.add(source_name)
            continue

        try:
            result = source.fetch_ratings(entry.media_type, entry.ids, abort_flag)
        except RateLimitHit as e:
            wait = e.retry_after_seconds if e.retry_after_seconds else 60.0
            paused_until[source_name] = time.time() + wait
            still_missing.add(source_name)
            log("Ratings", f"   {source_name}: 429 in retry, deferring {wait:.1f}s", xbmc.LOGDEBUG)
            continue
        except RetryableError as e:
            still_missing.add(source_name)
            seen = {f.get("source") for f in entry.failures}
            if source_name not in seen:
                entry.failures.append({"source": source_name, "reason": e.reason})
            continue
        except Exception as e:
            log("Ratings", f"   {source_name}: Retry failed: {e}", xbmc.LOGDEBUG)
            still_missing.add(source_name)
            continue

        if result:
            new_ratings.append(result)
            entry.sources_used.append(source_name)
        else:
            still_missing.add(source_name)

    if not new_ratings:
        entry.missing_sources = still_missing
        return False

    merged_new = merge_ratings(new_ratings)
    final_ratings = dict(entry.applied_ratings)
    for name, data in merged_new.items():
        new_val = data.get("rating")
        if new_val is None:
            continue
        new_votes = float(data.get("votes", 0))
        existing = final_ratings.get(name)
        if existing is None or new_votes > float(existing.get("votes", 0)):
            final_ratings[name] = {"rating": new_val, "votes": new_votes}

    method_info = KODI_SET_DETAILS_METHODS.get(entry.media_type)
    if not method_info:
        entry.missing_sources = still_missing
        return False
    method, id_key = method_info

    kodi_ratings = prepare_kodi_ratings(final_ratings, default_source="imdb")
    response = request(method, {id_key: entry.dbid, "ratings": kodi_ratings})

    if response is None:
        entry.missing_sources = still_missing
        return False

    db.update_synced_ratings(
        entry.media_type, entry.dbid, final_ratings, build_external_ids(entry.ids)
    )
    entry.applied_ratings = final_ratings
    entry.missing_sources = still_missing

    return not still_missing


def prompt_and_process_retries(retry_queue: List[RetryPoolEntry], media_type: str,
                               sources: List, source_mode: str) -> int:
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
            return _process_retry_queue(retry_queue, media_type, sources, source_mode)

        else:
            log("Ratings",
                f"User skipped retry of {count} item{'s' if count > 1 else ''}",
                xbmc.LOGINFO)
            return 0


def _process_retry_queue(retry_queue: List[RetryPoolEntry], media_type: str,
                         sources: List, source_mode: str) -> int:
    """Run targeted retries for queued entries; only the missing sources are fetched.

    On 429, the offending source is paused for the remainder of this pass per
    Retry-After. Returns count of entries fully resolved.
    """
    progress = DialogProgress()
    progress.create(ADDON.getLocalizedString(32300), ADDON.getLocalizedString(32310))

    success_count = 0
    total = len(retry_queue)
    paused_until: Dict[str, float] = {}

    for i, entry in enumerate(retry_queue):
        if progress.iscanceled():
            break

        percent = int((i / max(total, 1)) * 100)
        progress.update(
            percent,
            f"{ADDON.getLocalizedString(32311).format(i+1, total)}\n{entry.title}"
        )

        if source_mode == "imdb":
            success, _ = update_single_item_imdb(entry.item, media_type)
        else:
            success = retry_targeted(entry, sources, paused_until)

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
