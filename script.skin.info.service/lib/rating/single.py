"""Single-item ratings flow: ID resolution, dataset lookup, merge+apply, update_single_item."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
from typing import Dict, Final, List, Optional, Tuple

import xbmc

from lib.kodi.client import request, log, KODI_SET_DETAILS_METHODS
from lib.kodi.settings import KodiSettings
from lib.data.api.tmdb import resolve_tmdb_id
from lib.data.api.imdb import get_imdb_dataset
from lib.data.api.client import RateLimitHit, RetryableError
from lib.data.api import tracker as usage_tracker
from lib.data.database import workflow as db
from lib.infrastructure.tasks import ShutdownAbortFlag
from lib.rating.merger import (merge_ratings, prepare_kodi_ratings, has_alias_drift, default_moved,
                               format_rating_change, rating_display_changed)
from lib.rating.ids import (
    get_imdb_id_from_tmdb,
    build_external_ids,
    get_tvshow_uniqueid,
)

_MAX_TOTAL_WAIT: Final = 30.0


def resolve_item_ids(item: Dict, media_type: str) -> Optional[Dict]:
    """Resolve external IDs for a library item; returns `None` when no usable IDs are found."""
    uniqueid = item.get("uniqueid", {})

    if media_type == "episode":
        tvshow_dbid = item.get("tvshowid")
        if not tvshow_dbid:
            return None
        tvshow_uniqueid = get_tvshow_uniqueid(tvshow_dbid)
        if not tvshow_uniqueid:
            return None
        show_imdb = tvshow_uniqueid.get("imdb")
        episode_imdb = uniqueid.get("imdb")
        season_num = item.get("season")
        episode_num = item.get("episode")
        if not episode_imdb and show_imdb:
            dataset = get_imdb_dataset()
            episode_imdb = dataset.get_episode_imdb_id(
                show_imdb,
                season_num or 0,
                episode_num or 0,
            )
        if not episode_imdb:
            episode_imdb = get_imdb_id_from_tmdb(
                media_type, tvshow_uniqueid, season_num, episode_num,
            )
        ids = {
            "tmdb": tvshow_uniqueid.get("tmdb"),
            "imdb": show_imdb,
            "imdb_episode": episode_imdb,
            "tvdb": tvshow_uniqueid.get("tvdb"),
            "season": str(item.get("season", "")),
            "episode": str(item.get("episode", "")),
        }
    else:
        raw_tmdb = uniqueid.get("tmdb")
        raw_imdb = uniqueid.get("imdb")
        if not raw_imdb:
            raw_imdb = get_imdb_id_from_tmdb(media_type, uniqueid)
        ids = {
            "tmdb": resolve_tmdb_id(raw_tmdb, raw_imdb, media_type),
            "imdb": raw_imdb,
            "tvdb": uniqueid.get("tvdb"),
        }

    if not ids.get("tmdb") and not ids.get("imdb") and not ids.get("imdb_episode"):
        return None

    return ids


def get_imdb_dataset_rating(ids: Dict, media_type: str) -> Tuple[List[Dict], List[str]]:
    """Look up IMDb dataset rating for item IDs; returns `(initial_ratings, initial_sources)`."""
    imdb_id = ids.get("imdb_episode") if media_type == "episode" else ids.get("imdb")
    if imdb_id:
        imdb_dataset = get_imdb_dataset()
        imdb_rating = imdb_dataset.get_rating(imdb_id)
        if imdb_rating:
            return [{"imdb": imdb_rating, "_source": "imdb_dataset"}], ["imdb_dataset"]
    return [], []


def merge_and_apply_ratings(
    media_type: str,
    dbid: int,
    title: str,
    year: Optional[str],
    all_ratings: List[Dict],
    sources_used: List[str],
    existing_ratings: Dict,
    ids: Dict,
    retryable_failures: Optional[List[dict]] = None,
) -> Tuple[Optional[bool], Optional[Dict]]:
    """Merge fetched ratings, apply to Kodi library, and sync to DB."""
    if retryable_failures is None:
        retryable_failures = []

    if not all_ratings:
        log("Ratings", "No ratings returned from any source", xbmc.LOGDEBUG)
        if retryable_failures:
            existing_normalized = {
                name: {"rating": d.get("rating", 0), "votes": float(d.get("votes", 0))}
                for name, d in existing_ratings.items()
                if isinstance(d, dict) and d.get("rating") is not None
            }
            return False, {
                "title": title, "year": year,
                "sources_used": [], "ratings_added": 0, "ratings_updated": 0,
                "added_details": [], "updated_details": [],
                "retryable_failures": retryable_failures,
                "final_ratings": existing_normalized,
            }
        return False, None

    merged = merge_ratings(all_ratings)

    final_ratings: Dict[str, Dict[str, float]] = {}
    for rating_name, rating_data in existing_ratings.items():
        if isinstance(rating_data, dict) and rating_data.get("rating") is not None:
            final_ratings[rating_name] = {
                "rating": rating_data["rating"],
                "votes": float(rating_data.get("votes", 0)),
            }

    added_ratings: List[str] = []
    updated_ratings: List[str] = []
    for rating_name, rating_data in merged.items():
        new_val = rating_data.get("rating")
        if new_val is None:
            continue
        new_votes = float(rating_data.get("votes", 0))

        if rating_name in final_ratings:
            old_val = final_ratings[rating_name]["rating"]
            old_votes = final_ratings[rating_name]["votes"]

            # a changed value wins even on fewer votes; providers renormalize their counts
            if new_votes > old_votes or rating_display_changed(old_val, new_val):
                final_ratings[rating_name] = {"rating": new_val, "votes": new_votes}
                if rating_display_changed(old_val, new_val):
                    updated_ratings.append(format_rating_change(
                        rating_name, old_val, int(old_votes), new_val, int(new_votes)))
        else:
            final_ratings[rating_name] = {"rating": new_val, "votes": new_votes}
            added_ratings.append(f"{rating_name} ({new_val:.1f})")

    supplied = set(merged)
    kodi_ratings = prepare_kodi_ratings(
        final_ratings, default_source=KodiSettings.ratings_default_source(), supplied=supplied)

    if added_ratings:
        log("Ratings", f"Added ratings: {', '.join(added_ratings)}", xbmc.LOGDEBUG)
    if updated_ratings:
        log("Ratings", f"Updated ratings: {' | '.join(updated_ratings)}", xbmc.LOGDEBUG)

    if (not added_ratings and not updated_ratings
            and not has_alias_drift(existing_ratings, supplied)
            and not default_moved(existing_ratings, kodi_ratings)):
        db.update_synced_ratings(
            media_type, dbid, final_ratings, build_external_ids(ids, media_type))
        return True, {
            "title": title, "year": year,
            "sources_used": sources_used, "ratings_added": 0, "ratings_updated": 0,
            "added_details": [], "updated_details": [],
            "retryable_failures": retryable_failures,
            "final_ratings": final_ratings,
        }

    method_info = KODI_SET_DETAILS_METHODS.get(media_type)
    if not method_info:
        return False, None
    method, id_key = method_info

    response = request(method, {id_key: dbid, "ratings": kodi_ratings})

    if response is not None:
        db.update_synced_ratings(
            media_type, dbid, final_ratings, build_external_ids(ids, media_type))

    item_stats = {
        "title": title, "year": year,
        "sources_used": sources_used,
        "ratings_added": len(added_ratings),
        "ratings_updated": len(updated_ratings),
        "added_details": added_ratings,
        "updated_details": updated_ratings,
        "retryable_failures": retryable_failures,
        "final_ratings": final_ratings,
    }

    return response is not None, item_stats


def update_single_item(
    item: Dict,
    media_type: str,
    sources: List,
    abort_flag=None,
    force_refresh: bool = True,
) -> tuple[Optional[bool], Optional[Dict]]:
    """Update one item's ratings from the dataset and every source; batch runs use the executor."""
    if abort_flag is None:
        abort_flag = ShutdownAbortFlag()

    dbid = item.get("movieid") or item.get("episodeid") or item.get("tvshowid")
    if not dbid:
        return False, None

    title = item.get("title", "Unknown")
    year = item.get("year")
    existing_ratings = item.get("ratings", {})

    ids = resolve_item_ids(item, media_type)
    if ids is None:
        return None, None

    if abort_flag and abort_flag.is_requested():
        return None, None

    all_ratings, sources_used = get_imdb_dataset_rating(ids, media_type)
    all_ratings = list(all_ratings)
    sources_used = list(sources_used)

    retryable_failures: list[dict] = []

    if not sources:
        return merge_and_apply_ratings(
            media_type=media_type, dbid=dbid, title=title, year=year, ids=ids,
            all_ratings=all_ratings, sources_used=sources_used,
            existing_ratings=existing_ratings, retryable_failures=retryable_failures,
        )

    start_time = time.time()

    executor = ThreadPoolExecutor(max_workers=len(sources))
    try:
        futures = {
            executor.submit(
                source.fetch_ratings, media_type, ids, abort_flag, force_refresh
            ): source
            for source in sources
        }
        pending = set(futures.keys())

        while pending:
            if abort_flag and abort_flag.is_requested():
                return None, None

            if (time.time() - start_time) > _MAX_TOTAL_WAIT:
                for future in pending:
                    source = futures[future]
                    source_name = source.provider_name
                    retryable_failures.append({"source": source_name, "reason": "timeout"})
                    log("Ratings",
                        f"   {source_name}: Timeout after {_MAX_TOTAL_WAIT}s",
                        xbmc.LOGDEBUG)
                break

            try:
                for future in as_completed(pending, timeout=1.0):
                    pending.discard(future)
                    source = futures[future]
                    source_name = source.provider_name

                    try:
                        ratings = future.result()
                        if ratings:
                            all_ratings.append(ratings)
                            sources_used.append(source_name)
                    except RateLimitHit as e:
                        action = usage_tracker.handle_rate_limit_error(e.provider)
                        if action == "cancel_all":
                            if abort_flag:
                                abort_flag.request()
                            return None, None
                        if action == "cancel_batch":
                            return None, None
                        if action == "retry":
                            retryable_failures.append(
                                {"source": source_name, "reason": "rate limit (user chose wait)"}
                            )
                        log("Ratings", f"   {source_name}: Rate limit reached", xbmc.LOGDEBUG)
                    except RetryableError as e:
                        log("Ratings",
                            f"   {source_name}: Retryable error: {e.reason}",
                            xbmc.LOGDEBUG)
                        retryable_failures.append({"source": source_name, "reason": e.reason})
                    except Exception as e:
                        log("Ratings", f"   {source_name}: Failed: {str(e)}", xbmc.LOGDEBUG)

            except FuturesTimeoutError:
                continue
    finally:
        executor.shutdown(wait=False)

    return merge_and_apply_ratings(
        media_type=media_type,
        dbid=dbid,
        title=title,
        year=year,
        all_ratings=all_ratings,
        sources_used=sources_used,
        existing_ratings=existing_ratings,
        ids=ids,
        retryable_failures=retryable_failures,
    )
