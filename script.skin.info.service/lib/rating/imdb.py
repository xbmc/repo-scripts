"""IMDb-only ratings: incremental sync, batch/single update, dataset/correction helpers."""
from __future__ import annotations

import time
from typing import Dict, List, NamedTuple, Optional, Set, Tuple, Final

import xbmc
import xbmcgui

from lib.infrastructure import tasks as task_manager
from lib.kodi.client import (
    request, batch_request, get_library_items, format_item_label, log,
    KODI_SET_DETAILS_METHODS, ADDON,
)
from lib.data.api.imdb import get_imdb_dataset
from lib.kodi.settings import KodiSettings
from lib.data.database import workflow as db
from lib.infrastructure.dialogs import show_textviewer, show_yesnocustom
from lib.rating.ids import (get_tvshow_uniqueid, prefetch_tvshow_uniqueids,
                            update_kodi_uniqueid)
from lib.rating.merger import format_rating_change, rating_display_changed


PROGRESS_SAVE_SECONDS: Final = 60

_DRIP_DELAY = {
    "idle": {"movie": 0, "tvshow": 0, "episode": 0},
    "library": {"movie": 500, "tvshow": 1500, "episode": 1500},
}
_PLAYBACK_POLL_MS: Final = 10000
_RESUME_GRACE_S: Final = 300
_SYNC_FLUSH_SIZE: Final = 50


class ImdbUpdate(NamedTuple):
    """One item's pending IMDb write; `kodi_ratings` is None when Kodi already matches."""
    dbid: int
    kodi_ratings: Optional[Dict]
    imdb_id: str
    new_rating: float
    new_votes: int
    title: str
    year: str
    is_add: bool
    old_rating: Optional[float]
    old_votes: int


def _needs_write(old_rating: Optional[float], old_votes: int,
                 new_rating: float, new_votes: int, *, gated: bool) -> bool:
    """True when Kodi is far enough from the dataset to rewrite it."""
    if old_rating is None:
        return True
    if rating_display_changed(old_rating, new_rating):
        return True
    if not gated:
        return new_votes != old_votes
    if not old_votes:
        return new_votes > 0
    swing = abs(new_votes - old_votes) / old_votes
    return swing > (0.1 if old_votes < 1000 else 0.05)


def _get_kodi_state() -> str:
    """What Kodi is busy with, for pacing the update."""
    if xbmc.getCondVisibility("Player.HasVideo"):
        return "playing"
    if xbmc.getCondVisibility("Window.IsVisible(10025)"):
        return "library"
    return "idle"


def _wait_until_video_idle(monitor: xbmc.Monitor) -> bool:
    """Wait for video playback to stay stopped through the grace period; False on abort."""
    while True:
        while xbmc.getCondVisibility("Player.HasVideo"):
            if monitor.waitForAbort(_PLAYBACK_POLL_MS / 1000):
                return False

        idle_since = time.time()
        restarted = False
        while time.time() - idle_since < _RESUME_GRACE_S:
            if monitor.waitForAbort(_PLAYBACK_POLL_MS / 1000):
                return False
            if xbmc.getCondVisibility("Player.HasVideo"):
                restarted = True
                break

        if not restarted:
            return True


def update_changed_imdb_ratings(
    media_type: str = "", monitor: Optional[xbmc.Monitor] = None
) -> Dict[str, int]:
    """Apply changed IMDb ratings, sync new items, returning `{updated, skipped, failed}`."""
    stats = {"updated": 0, "skipped": 0, "failed": 0}

    changed_items = db.get_imdb_changed_items(media_type if media_type else None)
    items_by_type: Dict[str, List[Dict]] = {}
    for item in changed_items:
        t = item["media_type"]
        if t not in items_by_type:
            items_by_type[t] = []
        items_by_type[t].append(item)

    changed_keys = {(item["media_type"], item["dbid"]) for item in changed_items}
    new_batch_items, new_skipped, title_map = _collect_new_library_items(
        media_type, monitor, changed_keys
    )
    stats["skipped"] += new_skipped

    new_by_type: Dict[str, List[Dict]] = {}
    for mtype, batch_items in new_batch_items:
        new_by_type[mtype] = batch_items

    total_new = sum(len(bi) for bi in new_by_type.values())
    combined_total = len(changed_items) + total_new

    if combined_total == 0:
        return stats

    if changed_items:
        from lib.data.database.imdb import get_dataset_stats
        generation = get_dataset_stats().get("last_modified") or "unknown"
        log("Ratings",
            f"Found {len(changed_items)} items with changed IMDb ratings "
            f"against dataset {generation}",
            xbmc.LOGINFO)
    if total_new:
        log("Ratings", f"Found {total_new} new library items to sync", xbmc.LOGINFO)

    work_items: List[Tuple[str, Dict]] = []
    for mtype in ["movie", "tvshow", "episode"]:
        for item in items_by_type.get(mtype, []):
            work_items.append((mtype, item))
        for item in new_by_type.get(mtype, []):
            work_items.append((mtype, item))

    if not monitor:
        monitor = xbmc.Monitor()

    sync_batch: List[tuple] = []
    imdb_default = KodiSettings.ratings_default_source() == "imdb"
    heading = ADDON.getLocalizedString(32318)
    progress = xbmcgui.DialogProgressBG()
    progress.create(heading)

    for idx, (item_media_type, item) in enumerate(work_items):
        if monitor.abortRequested():
            log("Ratings", "Abort requested, stopping incremental update", xbmc.LOGINFO)
            break

        pct = int((idx / combined_total) * 100)
        label = (item.get("title") or title_map.get((item_media_type, item["dbid"]))
                 or item.get("imdb_id", ""))
        progress.update(pct, heading,
                        ADDON.getLocalizedString(32306).format(idx + 1, combined_total, label))

        state = _get_kodi_state()
        if state == "playing":
            if sync_batch:
                db.update_synced_ratings_batch(sync_batch)
                sync_batch = []
            progress.close()
            if not _wait_until_video_idle(monitor):
                break
            progress.create(heading)
            state = _get_kodi_state()

        set_method_info = KODI_SET_DETAILS_METHODS.get(item_media_type)
        if not set_method_info:
            stats["failed"] += 1
            continue

        if not item.get("imdb_id"):
            stats["skipped"] += 1
            continue

        set_method, set_id_key = set_method_info
        response = request(set_method, {
            set_id_key: item["dbid"],
            "ratings": {
                "imdb": {"rating": item["new_rating"], "votes": item["new_votes"],
                         "default": imdb_default}
            }
        })

        if response is not None and "error" not in response:
            sync_batch.append((
                item_media_type, item["dbid"],
                item["imdb_id"], item["new_rating"], item["new_votes"]
            ))
            is_new = item.get('old_rating', 0.0) == 0.0 and item.get('old_votes', 0) == 0
            if is_new:
                log("Ratings", f"Added {item['imdb_id']}: imdb ({item['new_rating']:.1f})",
                    xbmc.LOGDEBUG)
            else:
                change = format_rating_change(
                    "imdb",
                    item.get('old_rating'), item.get('old_votes', 0) or 0,
                    item['new_rating'], item['new_votes'])
                log("Ratings", f"Updated {item['imdb_id']}: {change}", xbmc.LOGDEBUG)
            stats["updated"] += 1
        else:
            log("Ratings",
                f"Failed {item['imdb_id']}: {item_media_type} dbid={item['dbid']} "
                "(stale or invalid)",
                xbmc.LOGDEBUG)
            db.clear_synced_ratings(item_media_type, item["dbid"])
            stats["failed"] += 1

        if len(sync_batch) >= _SYNC_FLUSH_SIZE:
            db.update_synced_ratings_batch(sync_batch)
            sync_batch = []

        delay_ms = _DRIP_DELAY.get(state, _DRIP_DELAY["idle"]).get(item_media_type, 100)
        if delay_ms > 0:
            xbmc.sleep(delay_ms)

    progress.close()

    if sync_batch:
        db.update_synced_ratings_batch(sync_batch)

    total = stats["updated"] + stats["skipped"] + stats["failed"]
    if total > 0:
        log("Ratings",
            f"Incremental update complete: {stats['updated']} updated, "
            f"{stats['skipped']} skipped, {stats['failed']} failed",
            xbmc.LOGINFO)
    return stats


def _collect_new_library_items(
    media_type: str, monitor: Optional[xbmc.Monitor] = None,
    wanted_titles: Optional[Set[Tuple[str, int]]] = None
) -> Tuple[List[Tuple[str, List[Dict]]], int, Dict[Tuple[str, int], str]]:
    """Library items never synced; ones already matching the dataset are recorded, not queued."""
    skipped = 0
    media_types = [media_type] if media_type else ["movie", "tvshow", "episode"]
    dataset = get_imdb_dataset()
    all_batch_items: List[Tuple[str, List[Dict]]] = []
    title_map: Dict[Tuple[str, int], str] = {}
    sync_batch_size = 5000

    for mtype in media_types:
        if monitor and monitor.abortRequested():
            break

        synced_dbids = db.get_synced_dbids(mtype)
        id_key = {"movie": "movieid", "tvshow": "tvshowid", "episode": "episodeid"}.get(mtype)
        if not id_key:
            continue

        props = ["uniqueid", "ratings", "title"]
        if mtype == "episode":
            props.extend(["season", "episode", "tvshowid", "showtitle"])

        items = get_library_items([mtype], properties=props)
        if not items:
            continue

        if mtype == "episode":
            unsynced_shows: Set[int] = {
                item["tvshowid"] for item in items
                if item.get("tvshowid")
                and item.get(id_key) and item.get(id_key) not in synced_dbids
            }
            if len(unsynced_shows) > 30:
                prefetch_tvshow_uniqueids(unsynced_shows)

        new_items = []
        imdb_ids_needed: List[str] = []
        for item in items:
            dbid = item.get(id_key)
            if not dbid:
                continue
            if wanted_titles and (mtype, dbid) in wanted_titles:
                title_map[(mtype, dbid)] = format_item_label(item, mtype)
            if dbid in synced_dbids:
                continue
            imdb_id = resolve_imdb_id(item, mtype, dataset)
            if not imdb_id:
                continue
            new_items.append(item)
            imdb_ids_needed.append(imdb_id)

        if not new_items:
            continue

        ratings_map = dataset.get_ratings_batch(imdb_ids_needed)

        batch_items: List[Dict] = []
        unchanged_syncs: List[tuple] = []
        type_skipped = 0
        for item, imdb_id in zip(new_items, imdb_ids_needed):
            rating_data = ratings_map.get(imdb_id)
            if not rating_data:
                skipped += 1
                type_skipped += 1
                continue

            existing_imdb = item.get("ratings", {}).get("imdb", {})
            existing_rating = existing_imdb.get("rating") if existing_imdb else None

            if (existing_rating is not None and not _needs_write(
                    existing_rating, int(existing_imdb.get("votes") or 0),
                    rating_data["rating"], int(rating_data["votes"]), gated=True)):
                unchanged_syncs.append(
                    (mtype, item[id_key], imdb_id,
                     rating_data["rating"], existing_imdb.get("votes") or 0)
                )

                if len(unchanged_syncs) >= sync_batch_size:
                    db.update_synced_ratings_batch(unchanged_syncs)
                    unchanged_syncs = []
                continue

            batch_items.append({
                "dbid": item[id_key],
                "imdb_id": imdb_id,
                "title": format_item_label(item, mtype),
                "new_rating": rating_data["rating"],
                "new_votes": rating_data["votes"],
                "old_rating": 0.0,
                "old_votes": 0,
            })

        if unchanged_syncs:
            db.update_synced_ratings_batch(unchanged_syncs)

        total_synced = len(new_items) - len(batch_items) - type_skipped
        if total_synced > 0:
            log("Ratings", f"Recorded {total_synced} already-synced {mtype} items", xbmc.LOGINFO)

        if batch_items:
            all_batch_items.append((mtype, batch_items))

    return all_batch_items, skipped, title_map


def run_imdb_batch(
    media_type: str,
    items: List[Dict],
    progress: xbmcgui.DialogProgress | xbmcgui.DialogProgressBG,
    results: Dict,
    ctx: task_manager.TaskContext,
    monitor: xbmc.Monitor,
    dataset_date: str,
    processed_ids: Set[int],
    gated: bool = False,
) -> None:
    """Run the IMDb dataset batch update, filling the results and processed ids in place."""

    def _should_abort() -> bool:
        return ctx.abort_flag.is_requested() or monitor.abortRequested()

    def _update_progress() -> None:
        current_count = len(processed_ids)
        percent = int((current_count / len(items)) * 100)
        if isinstance(progress, xbmcgui.DialogProgressBG):
            progress.update(
                percent, ADDON.getLocalizedString(32318),
                ADDON.getLocalizedString(32308).format(current_count, len(items))
            )
        elif isinstance(progress, xbmcgui.DialogProgress):
            progress.update(
                percent, ADDON.getLocalizedString(32309).format(current_count, len(items))
            )

    log("Ratings", f"Using BATCHED IMDb update for {len(items)} {media_type} items", xbmc.LOGINFO)
    batch_items_prepared = 0
    batch_items_skipped = 0
    id_key = (
        "movieid" if media_type == "movie"
        else "tvshowid" if media_type == "tvshow" else "episodeid"
    )
    set_method_info = KODI_SET_DETAILS_METHODS.get(media_type)
    if not set_method_info:
        log("Ratings", f"Unknown media type for SET: {media_type}", xbmc.LOGERROR)
        return

    set_method, set_id_key = set_method_info
    last_progress_save = time.monotonic()
    dataset = get_imdb_dataset()

    batch_start = 0
    while batch_start < len(items):
        if _should_abort():
            results["cancelled"] = True
            break

        if isinstance(progress, xbmcgui.DialogProgress) and progress.iscanceled():
            results["cancelled"] = True
            break

        batch_end = min(batch_start + 1000, len(items))
        batch = items[batch_start:batch_end]

        set_calls = []
        items_to_update = []
        unchanged_syncs: List[tuple] = []

        pending_items = []
        for item in batch:
            dbid = item.get(id_key)
            if dbid and dbid in processed_ids:
                continue
            imdb_id = resolve_imdb_id(item, media_type, dataset)
            pending_items.append((item, imdb_id))

        all_imdb_ids = [iid for _, iid in pending_items if iid]
        batch_ratings = dataset.get_ratings_batch(all_imdb_ids) if all_imdb_ids else {}

        for item, resolved_imdb_id in pending_items:
            if _should_abort():
                log("Ratings", "Abort requested during item preparation", xbmc.LOGINFO)
                results["cancelled"] = True
                break

            dbid = item.get(id_key)

            prepared = prepare_imdb_update(
                item, media_type, dataset,
                ratings_map=batch_ratings, resolved_imdb_id=resolved_imdb_id, gated=gated
            )
            if prepared is None:
                results["skipped"] += 1
                batch_items_skipped += 1
                if dbid:
                    processed_ids.add(dbid)
                continue

            dbid = prepared.dbid

            if prepared.kodi_ratings is None:
                unchanged_syncs.append((media_type, dbid, prepared.imdb_id,
                                        prepared.new_rating, prepared.old_votes))
                processed_ids.add(dbid)
                continue

            batch_items_prepared += 1
            set_calls.append({
                "method": set_method,
                "params": {set_id_key: dbid, "ratings": prepared.kodi_ratings}
            })
            items_to_update.append(prepared)

        if results.get("cancelled"):
            break

        if set_calls:
            _update_progress()
            set_responses = batch_request(set_calls)

            if _should_abort():
                log("Ratings", "Abort requested after batch_request", xbmc.LOGINFO)
                results["cancelled"] = True
                break

            sync_batch: List[tuple] = []
            for i, update_info in enumerate(items_to_update):
                if _should_abort():
                    log("Ratings", "Abort requested during DB update loop", xbmc.LOGINFO)
                    results["cancelled"] = True
                    break

                response = set_responses[i] if i < len(set_responses) else None
                dbid = update_info.dbid

                if response is not None and "error" not in response:
                    sync_batch.append((
                        media_type, dbid,
                        update_info.imdb_id, update_info.new_rating, update_info.new_votes
                    ))
                    action = "Added" if update_info.is_add else "Updated"
                    change = (f"imdb {update_info.new_rating:.1f}, "
                              f"votes {update_info.new_votes}" if update_info.is_add
                              else format_rating_change(
                                  "imdb",
                                  update_info.old_rating, update_info.old_votes,
                                  update_info.new_rating, update_info.new_votes))
                    log("Ratings", f"{action} {update_info.title}: {change}", xbmc.LOGDEBUG)
                    results["updated"] += 1
                    if update_info.is_add:
                        results["total_ratings_added"] += 1
                    else:
                        results["total_ratings_updated"] += 1
                else:
                    results["failed"] += 1

                processed_ids.add(dbid)

            if sync_batch:
                db.update_synced_ratings_batch(sync_batch)

            if results.get("cancelled"):
                break

        if unchanged_syncs:
            db.update_synced_ratings_batch(unchanged_syncs)

        ctx.mark_progress()
        _update_progress()

        if time.monotonic() - last_progress_save >= PROGRESS_SAVE_SECONDS:
            db.save_imdb_update_progress(media_type, dataset_date, processed_ids)
            last_progress_save = time.monotonic()

        batch_start = batch_end

    log("Ratings",
        f"BATCHED complete: {batch_items_prepared} to update, {batch_items_skipped} skipped",
        xbmc.LOGINFO)

    if not results.get("cancelled"):
        db.clear_imdb_update_progress(media_type)
    elif dataset_date:
        db.save_imdb_update_progress(media_type, dataset_date, processed_ids)


def ensure_episode_dataset(
    progress: xbmcgui.DialogProgress | xbmcgui.DialogProgressBG | None = None
) -> None:
    """Refresh episode IMDb ID dataset when library count changes or IMDb updates; else no-op."""
    library_ep_count_str = xbmc.getInfoLabel('Window(Home).Property(Episodes.Count)')
    try:
        library_ep_count = int(library_ep_count_str) if library_ep_count_str else 0
    except ValueError:
        library_ep_count = 0

    if library_ep_count == 0:
        return

    dataset = get_imdb_dataset()

    if not dataset.needs_episode_refresh(library_ep_count):
        return

    shows = get_library_items(["tvshow"], properties=["uniqueid"])
    user_show_ids: set[str] = set()
    for show in shows:
        imdb_id = show.get("uniqueid", {}).get("imdb")
        if imdb_id:
            user_show_ids.add(imdb_id)

    if not user_show_ids:
        log("Ratings", "No TV shows with IMDb IDs, skipping episode dataset refresh")
        return

    if progress:
        if isinstance(progress, xbmcgui.DialogProgressBG):
            progress.update(0, ADDON.getLocalizedString(32318), ADDON.getLocalizedString(32312))
        elif isinstance(progress, xbmcgui.DialogProgress):
            progress.update(0, ADDON.getLocalizedString(32312))

    def progress_callback(status: str) -> None:
        if progress:
            if isinstance(progress, xbmcgui.DialogProgressBG):
                progress.update(0, ADDON.getLocalizedString(32318), status)
            elif isinstance(progress, xbmcgui.DialogProgress):
                progress.update(0, status)

    dataset.refresh_episode_dataset(user_show_ids, library_ep_count, progress_callback)


def prompt_imdb_corrections(pending: List[Dict]) -> int:
    """Prompt to apply outdated IMDb id corrections, or list them; returns how many applied."""
    count = len(pending)
    message = (
        f"{ADDON.getLocalizedString(32422).format(count)}\n\n{ADDON.getLocalizedString(32423)}"
    )

    while True:
        result = show_yesnocustom(
            ADDON.getLocalizedString(32421),
            message,
            customlabel=ADDON.getLocalizedString(32427),
        )

        if result == 2:
            lines = [f"[B]{ADDON.getLocalizedString(32421)}[/B]", ""]
            for item in pending:
                title = item.get("title", "Unknown")
                year = item.get("year", "")
                year_str = f" ({year})" if year else ""
                old_id = item.get("old_id", "")
                new_id = item.get("new_id", "")
                lines.append(f"{title}{year_str}")
                lines.append(f"  {old_id} -> {new_id}")
                lines.append("")

            show_textviewer(ADDON.getLocalizedString(32421), "\n".join(lines))

        elif result == 1:
            corrected = 0
            for item in pending:
                success = update_kodi_uniqueid(
                    item["media_type"],
                    item["dbid"],
                    item["uniqueid"],
                    item["new_id"]
                )
                if success:
                    corrected += 1
                    log("Ratings",
                        f"Corrected IMDb ID: {item['old_id']} -> {item['new_id']} "
                        f"for {item['title']}",
                        xbmc.LOGINFO)

            return corrected

        else:
            log("Ratings",
                f"User skipped {count} IMDb ID correction{'s' if count > 1 else ''}",
                xbmc.LOGINFO)
            return 0


def resolve_imdb_id(item: Dict, media_type: str, dataset) -> Optional[str]:
    """Resolve an item's IMDb id, from the episode dataset for an episode lacking one."""
    uniqueid = item.get("uniqueid", {})

    if media_type == "episode":
        imdb_id = uniqueid.get("imdb")
        if imdb_id:
            return imdb_id
        tvshow_dbid = item.get("tvshowid")
        if tvshow_dbid:
            tvshow_uniqueid = get_tvshow_uniqueid(tvshow_dbid)
            if tvshow_uniqueid:
                show_imdb = tvshow_uniqueid.get("imdb")
                season_num = item.get("season")
                episode_num = item.get("episode")
                if show_imdb and season_num is not None and episode_num is not None:
                    return dataset.get_episode_imdb_id(show_imdb, season_num, episode_num)
        return None

    return uniqueid.get("imdb") or None


def prepare_imdb_update(
    item: Dict,
    media_type: str,
    dataset,
    db_cursor=None,
    ratings_map: Optional[Dict[str, Dict]] = None,
    resolved_imdb_id: Optional[str] = None,
    gated: bool = False,
) -> Optional[ImdbUpdate]:
    """Prepare one item's IMDb write; None when the item cannot be resolved."""
    dbid = item.get("movieid") or item.get("episodeid") or item.get("tvshowid")
    if not dbid:
        return None

    title = format_item_label(item, media_type) or "Unknown"
    year = item.get("year", "")
    existing_ratings = item.get("ratings", {})

    imdb_id = resolved_imdb_id or resolve_imdb_id(item, media_type, dataset)
    if not imdb_id:
        return None

    if ratings_map is not None:
        imdb_rating = ratings_map.get(imdb_id)
    else:
        imdb_rating = dataset.get_rating(imdb_id, cursor=db_cursor)
    if not imdb_rating:
        return None

    new_rating = imdb_rating["rating"]
    new_votes = imdb_rating["votes"]

    existing_imdb = existing_ratings.get("imdb", {})
    old_rating = existing_imdb.get("rating") if existing_imdb else None

    is_add = old_rating is None
    old_votes = int(existing_imdb.get("votes") or 0)
    if not _needs_write(old_rating, old_votes, new_rating, new_votes, gated=gated):
        # the sync row records Kodi's votes when no write happens
        return ImdbUpdate(dbid, None, imdb_id, new_rating, new_votes,
                          title, str(year) if year else "", False, old_rating, old_votes)

    kodi_ratings = {
        "imdb": {
            "rating": new_rating,
            "votes": new_votes,
            "default": KodiSettings.ratings_default_source() == "imdb",
        }
    }

    return ImdbUpdate(dbid, kodi_ratings, imdb_id, new_rating, new_votes,
                      title, str(year) if year else "", is_add, old_rating, old_votes)
