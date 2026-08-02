"""IMDb-only ratings: incremental sync, batch/single update, dataset/correction helpers."""
from __future__ import annotations

import time
from typing import Dict, List, Optional, Set, Tuple

import xbmc
import xbmcgui

from lib.infrastructure import tasks as task_manager
from lib.kodi.client import (
    request, batch_request, get_library_items, log,
    KODI_SET_DETAILS_METHODS, ADDON,
)
from lib.data.api.imdb import get_imdb_dataset
from lib.data.database import workflow as db
from lib.infrastructure.dialogs import show_textviewer, show_yesnocustom
from lib.rating.ids import get_tvshow_uniqueid, prefetch_tvshow_uniqueids, update_kodi_uniqueid


PROGRESS_SAVE_INTERVAL = 50

_RATING_EPSILON = 0.05  # IMDb ratings are 1-decimal; ignore sub-step drift from other scrapers

_DRIP_DELAY = {
    "idle": {"movie": 0, "tvshow": 0, "episode": 0},
    "library": {"movie": 500, "tvshow": 1500, "episode": 1500},
}
_PLAYBACK_POLL_MS = 10000
_RESUME_GRACE_S = 300
_SYNC_FLUSH_SIZE = 50


def _get_kodi_state() -> str:
    if xbmc.getCondVisibility("Player.HasVideo"):
        return "playing"
    if xbmc.getCondVisibility("Window.IsVisible(10025)"):
        return "library"
    return "idle"


def _wait_until_video_idle(monitor: xbmc.Monitor) -> bool:
    """Block until video playback has been stopped for `_RESUME_GRACE_S` straight.

    New playback during the grace window restarts the wait, so back-to-back
    episodes don't get update churn between them. Returns False on abort.
    """
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


def preserve_other_ratings(existing_ratings: Dict, kodi_ratings: Dict) -> None:
    """Copy non-imdb ratings from existing into kodi_ratings during IMDb-only updates."""
    for source_name, rating_data in existing_ratings.items():
        if source_name != "imdb" and isinstance(rating_data, dict):
            kodi_ratings[source_name] = {
                "rating": rating_data.get("rating", 0),
                "votes": int(rating_data.get("votes", 0)),
                "default": False,
            }


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
        log("Ratings", f"Found {len(changed_items)} items with changed IMDb ratings", xbmc.LOGINFO)
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
                "imdb": {"rating": item["new_rating"], "votes": item["new_votes"], "default": True}
            }
        })

        if response is not None and "error" not in response:
            sync_batch.append((
                item_media_type, item["dbid"], 'imdb',
                item["imdb_id"], item["new_rating"], item["new_votes"]
            ))
            is_new = item.get('old_rating', 0.0) == 0.0 and item.get('old_votes', 0) == 0
            if is_new:
                log("Ratings", f"Added {item['imdb_id']}: imdb ({item['new_rating']:.1f})",
                    xbmc.LOGDEBUG)
            else:
                log("Ratings",
                    f"Updated {item['imdb_id']}: imdb "
                    f"({item.get('old_rating', 0):.1f} -> {item['new_rating']:.1f})",
                    xbmc.LOGDEBUG)
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


def _item_label(item: Dict, media_type: str) -> str:
    if media_type == "episode":
        showtitle = item.get("showtitle")
        season = item.get("season")
        episode = item.get("episode")
        if showtitle and season is not None and episode is not None:
            return f"{showtitle} S{int(season):02d}E{int(episode):02d}"
    return item.get("title", "")


def _collect_new_library_items(
    media_type: str, monitor: Optional[xbmc.Monitor] = None,
    wanted_titles: Optional[Set[Tuple[str, int]]] = None
) -> Tuple[List[Tuple[str, List[Dict]]], int, Dict[Tuple[str, int], str]]:
    """Collect library items never synced to the IMDb dataset.

    Items whose Kodi rating already matches the dataset are batch-inserted directly
    into `ratings_synced` (skipping the JSON-RPC SET). `wanted_titles` is a set of
    `(media_type, dbid)` keys to resolve display labels for while the library is
    already being read. Returns `(batch_items_by_type, skipped_count, title_map)`.
    """
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
            # one bulk request costs about the same as ~30 per-show lookups
            if len(unsynced_shows) > 30:
                prefetch_tvshow_uniqueids(unsynced_shows)

        new_items = []
        imdb_ids_needed: List[str] = []
        for item in items:
            dbid = item.get(id_key)
            if not dbid:
                continue
            if wanted_titles and (mtype, dbid) in wanted_titles:
                title_map[(mtype, dbid)] = _item_label(item, mtype)
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

            if (existing_rating is not None
                    and abs(existing_rating - rating_data["rating"]) < _RATING_EPSILON):
                unchanged_syncs.append(
                    (mtype, item[id_key], 'imdb', imdb_id,
                     rating_data["rating"], rating_data["votes"])
                )

                if len(unchanged_syncs) >= sync_batch_size:
                    db.update_synced_ratings_batch(unchanged_syncs)
                    unchanged_syncs = []
                continue

            batch_items.append({
                "dbid": item[id_key],
                "imdb_id": imdb_id,
                "title": _item_label(item, mtype),
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
) -> None:
    """Run IMDb dataset batch update. Mutates `results` and `processed_ids` in place."""

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
    items_since_save = 0
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
                ratings_map=batch_ratings, resolved_imdb_id=resolved_imdb_id
            )
            if prepared is None:
                results["skipped"] += 1
                batch_items_skipped += 1
                if dbid:
                    processed_ids.add(dbid)
                continue

            dbid, kodi_ratings, imdb_id, new_rating, new_votes, title, year, is_add = prepared

            if kodi_ratings is None:
                unchanged_syncs.append((media_type, dbid, 'imdb', imdb_id, new_rating, new_votes))
                processed_ids.add(dbid)
                items_since_save += 1
                continue

            batch_items_prepared += 1
            set_calls.append({
                "method": set_method,
                "params": {set_id_key: dbid, "ratings": kodi_ratings}
            })
            items_to_update.append({
                "dbid": dbid,
                "imdb_id": imdb_id,
                "new_rating": new_rating,
                "new_votes": new_votes,
                "title": title,
                "year": year,
                "is_add": is_add
            })

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
                dbid = update_info["dbid"]

                if response is not None and "error" not in response:
                    sync_batch.append((
                        media_type, dbid, 'imdb',
                        update_info["imdb_id"], update_info["new_rating"], update_info["new_votes"]
                    ))
                    action = "Added" if update_info["is_add"] else "Updated"
                    log("Ratings",
                        f"{action} {update_info['title']}: "
                        f"imdb ({update_info['new_rating']:.1f})",
                        xbmc.LOGDEBUG)
                    results["updated"] += 1
                    if update_info["is_add"]:
                        results["total_ratings_added"] += 1
                    else:
                        results["total_ratings_updated"] += 1
                else:
                    results["failed"] += 1

                processed_ids.add(dbid)
                items_since_save += 1

            if sync_batch:
                db.update_synced_ratings_batch(sync_batch)

            if results.get("cancelled"):
                break

        if unchanged_syncs:
            db.update_synced_ratings_batch(unchanged_syncs)

        ctx.mark_progress()
        _update_progress()

        if items_since_save >= PROGRESS_SAVE_INTERVAL:
            db.save_imdb_update_progress(media_type, dataset_date, processed_ids, len(items))
            items_since_save = 0

        batch_start = batch_end

    log("Ratings",
        f"BATCHED complete: {batch_items_prepared} to update, {batch_items_skipped} skipped",
        xbmc.LOGINFO)

    if not results.get("cancelled"):
        db.clear_imdb_update_progress(media_type)
    elif dataset_date:
        db.save_imdb_update_progress(media_type, dataset_date, processed_ids, len(items))


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
    """3-button dialog (list / apply all / skip) for outdated IMDb IDs; returns count applied."""
    count = len(pending)
    message = (
        f"{ADDON.getLocalizedString(32422).format(count)}\n\n{ADDON.getLocalizedString(32423)}"
    )

    while True:
        result = show_yesnocustom(
            ADDON.getLocalizedString(32421),
            message,
            customlabel=ADDON.getLocalizedString(32427),
            nolabel=xbmc.getLocalizedString(106),
            yeslabel=xbmc.getLocalizedString(107)
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
    """Return the IMDb ID for an item, falling back to the episode-id dataset for episodes."""
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
) -> Optional[Tuple[int, Optional[Dict], str, float, int, str, str, bool]]:
    """Build (dbid, kodi_ratings, ...) tuple for an IMDb-only batch update; None on skip/no-op."""
    dbid = item.get("movieid") or item.get("episodeid") or item.get("tvshowid")
    if not dbid:
        return None

    title = item.get("title", "Unknown")
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
    if not is_add and abs(old_rating - new_rating) < _RATING_EPSILON:
        return (dbid, None, imdb_id, new_rating, new_votes, title, str(year) if year else "", False)

    kodi_ratings = {
        "imdb": {
            "rating": new_rating,
            "votes": new_votes,
            "default": True,
        }
    }
    preserve_other_ratings(existing_ratings, kodi_ratings)

    return (
        dbid, kodi_ratings, imdb_id, new_rating, new_votes,
        title, str(year) if year else "", is_add
    )


def update_single_item_imdb(item: Dict, media_type: str, abort_flag=None,
                            db_cursor=None) -> tuple[Optional[bool], Optional[Dict]]:
    """Apply IMDb-dataset rating to one item; `db_cursor` shares a connection across bulk ops."""
    dbid = item.get("movieid") or item.get("episodeid") or item.get("tvshowid")
    if not dbid:
        return False, None

    title = item.get("title", "Unknown")
    year = item.get("year")
    uniqueid = item.get("uniqueid", {})
    existing_ratings = item.get("ratings", {})

    season_num: Optional[int] = None
    episode_num: Optional[int] = None
    lookup_uniqueid = uniqueid

    if media_type == "episode":
        season_num = item.get("season")
        episode_num = item.get("episode")
        tvshow_dbid = item.get("tvshowid")
        if tvshow_dbid:
            tvshow_uniqueid = get_tvshow_uniqueid(tvshow_dbid)
            if tvshow_uniqueid:
                lookup_uniqueid = tvshow_uniqueid

    imdb_id = uniqueid.get("imdb") or None

    if not imdb_id and media_type == "episode":
        show_imdb = lookup_uniqueid.get("imdb")
        if show_imdb and season_num is not None and episode_num is not None:
            dataset = get_imdb_dataset()
            imdb_id = dataset.get_episode_imdb_id(show_imdb, season_num, episode_num)

    if not imdb_id:
        log("Ratings", f"Skipped (no IMDb ID): {title} ({year})", xbmc.LOGDEBUG)
        return None, None

    if abort_flag and abort_flag.is_requested():
        return None, None

    dataset = get_imdb_dataset()
    imdb_rating = dataset.get_rating(imdb_id, cursor=db_cursor)

    if not imdb_rating:
        log("Ratings", f"Skipped (no rating data): {title} ({year}) - {imdb_id}", xbmc.LOGDEBUG)
        return None, None

    new_rating = imdb_rating["rating"]
    new_votes = imdb_rating["votes"]

    existing_imdb = existing_ratings.get("imdb", {})
    old_rating = existing_imdb.get("rating") if existing_imdb else None

    added_ratings = []
    updated_ratings = []

    if old_rating is None:
        added_ratings.append(f"imdb ({new_rating:.1f})")
    elif abs(old_rating - new_rating) >= _RATING_EPSILON:
        updated_ratings.append(f"imdb ({old_rating:.1f} -> {new_rating:.1f})")
    else:
        return True, None

    kodi_ratings = {
        "imdb": {
            "rating": new_rating,
            "votes": new_votes,
            "default": True,
        }
    }

    preserve_other_ratings(existing_ratings, kodi_ratings)

    method_info = KODI_SET_DETAILS_METHODS.get(media_type)
    if not method_info:
        return False, None
    method, id_key = method_info

    response = request(method, {id_key: dbid, "ratings": kodi_ratings})

    if response is not None:
        db.update_synced_ratings(
            media_type, dbid,
            {"imdb": {"rating": new_rating, "votes": new_votes}},
            {"imdb": imdb_id}
        )

    item_stats = {
        "title": title,
        "year": year,
        "sources_used": ["imdb_dataset"],
        "ratings_added": len(added_ratings),
        "ratings_updated": len(updated_ratings),
        "added_details": added_ratings,
        "updated_details": updated_ratings,
    }

    return response is not None, item_stats
