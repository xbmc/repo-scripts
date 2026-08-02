"""Background updater: refreshes TTL-expired entries, invalidates passed `next_episode_to_air`."""
from __future__ import annotations

import threading
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, TYPE_CHECKING

import xbmc

from lib.kodi.client import log
from lib.data.database.cache import (
    get_cached_online_keys,
    get_cached_online_properties,
    cache_online_properties,
)
from lib.service.online.helpers import get_online_ttl, make_cache_key
from lib.service.online.fetchers import fetch_tmdb_online_data

if TYPE_CHECKING:
    from lib.service.online.main import OnlineServiceMain


UPDATER_PLAYBACK_POLL_S = 30
UPDATER_IDLE_S = 3600


class UpdaterHandler:
    """Refreshes TTL-expired schedule entries; never enumerates the library."""

    def __init__(self, service: 'OnlineServiceMain'):
        self._service = service
        self._thread: Optional[threading.Thread] = None
        self._restart = False

    def start(self) -> None:
        """Spawn the background updater thread (idempotent)."""
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def request_restart(self) -> None:
        """Request the updater to wake up and run a maintenance pass."""
        self._restart = True

    def _worker(self) -> None:
        try:
            self._run()
        except Exception as e:
            log("Service", f"Online updater error: {e}", xbmc.LOGWARNING)

    def _run(self) -> None:
        from lib.data.database.cache import get_cached_metadata
        from lib.data.database.schedule import (
            get_all_schedule, upsert_schedule, remove_schedule,
        )
        from lib.data.database.mapping import get_imdb_ids_batch

        monitor = xbmc.Monitor()
        abort = self._service.abort

        while not abort.is_set():
            self._restart = False
            today = datetime.now().strftime("%Y-%m-%d")

            schedule = get_all_schedule()
            if not schedule:
                self._idle_wait()
                continue

            self._prune_removed_shows(schedule, remove_schedule)
            schedule = get_all_schedule()
            if not schedule:
                self._idle_wait()
                continue

            imdb_map = get_imdb_ids_batch({s["tmdb_id"] for s in schedule}, "tvshow")
            shows = [
                {
                    "tmdb_id": s["tmdb_id"],
                    "imdb_id": imdb_map.get(s["tmdb_id"], ""),
                    "tvshowid": s["tvshowid"],
                    "title": s["title"],
                }
                for s in schedule
            ]

            stale_keys, stale_tmdb_ids = self._get_stale_schedule_keys(schedule, shows)
            if stale_keys:
                from lib.data.database.cache import (
                    invalidate_online_properties_by_keys, expire_metadata,
                )
                invalidate_online_properties_by_keys(stale_keys)
                for tmdb_id in stale_tmdb_ids:
                    expire_metadata("tvshow", tmdb_id, ttl_hours=0)

            cached_keys = get_cached_online_keys()
            expired = [
                s for s in shows
                if make_cache_key("tvshow", s.get("imdb_id") or "", s["tmdb_id"]) not in cached_keys
            ]

            if not expired:
                self._idle_wait()
                continue

            log("Service",
                f"Online updater: {len(expired)} expired, {len(shows) - len(expired)} cached",
                xbmc.LOGINFO)

            fetched = 0
            for show in expired:
                if abort.is_set() or self._restart:
                    break

                while xbmc.getCondVisibility("Player.HasVideo"):
                    if monitor.waitForAbort(UPDATER_PLAYBACK_POLL_S) or abort.is_set():
                        return

                tmdb_id = show["tmdb_id"]
                imdb_id = show.get("imdb_id") or ""
                cache_key = make_cache_key("tvshow", imdb_id, tmdb_id)

                self._service.updater_in_progress.add(cache_key)
                try:
                    tmdb_props = fetch_tmdb_online_data(
                        "tvshow", imdb_id, tmdb_id, self._service.abort_flag,
                    )
                    if tmdb_props:
                        existing = get_cached_online_properties(cache_key) or {}
                        existing.update(tmdb_props)
                        ttl = get_online_ttl("tvshow", tmdb_id)
                        cache_online_properties(cache_key, existing, ttl_hours=ttl)
                        fetched += 1
                finally:
                    self._service.updater_in_progress.discard(cache_key)

                tmdb_data = get_cached_metadata("tvshow", tmdb_id)
                if tmdb_data:
                    next_ep = tmdb_data.get("next_episode_to_air")
                    if next_ep and (next_ep.get("air_date") or "") < today:
                        next_ep = None
                    upsert_schedule(
                        tmdb_id, show["tvshowid"], show["title"],
                        tmdb_data.get("status") or "",
                        next_ep,
                        tmdb_data.get("last_episode_to_air"),
                    )

                if monitor.abortRequested():
                    break

            log("Service", f"Online updater: {fetched} refreshed", xbmc.LOGINFO)
            self._idle_wait()

    def _idle_wait(self) -> None:
        monitor = xbmc.Monitor()
        abort = self._service.abort
        elapsed = 0.0
        while elapsed < UPDATER_IDLE_S:
            if abort.is_set() or self._restart:
                break
            step = min(10.0, UPDATER_IDLE_S - elapsed)
            if monitor.waitForAbort(step):
                abort.set()
                break
            elapsed += step

    @staticmethod
    def _get_stale_schedule_keys(
        schedule: List[Dict], shows: List[Dict]
    ) -> Tuple[List[str], Set[str]]:
        """Find cache keys for shows whose `next_episode_air_date` has passed."""
        today = datetime.now().strftime("%Y-%m-%d")
        stale_tmdb_ids = set()
        for entry in schedule:
            next_air = entry.get("next_episode_air_date") or ""
            if next_air and next_air < today:
                stale_tmdb_ids.add(entry["tmdb_id"])
        if not stale_tmdb_ids:
            return [], set()
        keys = []
        for show in shows:
            if show["tmdb_id"] in stale_tmdb_ids:
                keys.append(make_cache_key(
                    "tvshow", show.get("imdb_id") or "", show["tmdb_id"]
                ))
        return keys, stale_tmdb_ids

    @staticmethod
    def _prune_removed_shows(schedule: List[Dict], remove_schedule) -> None:
        """Remove schedule entries for shows no longer in the user's library."""
        from lib.data.database.rollcall import get_valid_dbids
        valid_dbids = get_valid_dbids("tvshow")
        if not valid_dbids and schedule:
            # Library appears empty, could be transient (DB rebuild, etc); skip pruning to be safe.
            return
        valid_set = set(valid_dbids)
        stale = [s["tmdb_id"] for s in schedule if s.get("tvshowid") not in valid_set]
        for tmdb_id in stale:
            remove_schedule(tmdb_id)
        if stale:
            log("Service",
                f"Online updater: pruned {len(stale)} schedule entries for removed shows",
                xbmc.LOGDEBUG)
