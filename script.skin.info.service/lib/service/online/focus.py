"""Focus handler: monitors ListItem changes and sets `SkinInfo.Online.*` properties."""
from __future__ import annotations

import threading
from datetime import datetime
from typing import Optional, Set, TYPE_CHECKING

import xbmc

from lib.kodi.client import log
from lib.kodi.utilities import clear_group, batch_set_props, gui_transition_settled
from lib.data.database.cache import (
    get_cached_online_properties,
    cache_online_properties,
    get_cached_metadata,
)
from lib.data.database.schedule import upsert_schedule
from lib.service.online.helpers import (
    get_online_ttl,
    make_cache_key,
    resolve_ids_from,
    resolve_season_ids,
    SKININFO_PREFIX_MAP,
)
from lib.service.online.fetchers import fetch_all_online_data

if TYPE_CHECKING:
    from lib.service.online.main import OnlineServiceMain


ONLINE_PROPERTY_PREFIX = "SkinInfo.Online."


class FocusHandler:
    """Tracks focused library items and applies cached/fetched online properties."""

    def __init__(self, service: 'OnlineServiceMain'):
        self._service = service
        self._last_item_key: Optional[str] = None
        # guarded by _keys_lock: read+swapped from both the poll thread and fetch workers
        self._last_prop_keys: Set[str] = set()
        self._keys_lock = threading.Lock()
        self._fetch_thread: Optional[threading.Thread] = None
        self._fetch_for_key: Optional[str] = None

    def process(self) -> None:
        """Read focused ListItem; set cached props or kick off a background fetch."""
        if not gui_transition_settled():
            return
        dbid = xbmc.getInfoLabel("ListItem.DBID") or ""
        dbtype = xbmc.getInfoLabel("ListItem.DBType") or ""

        if not dbid or dbtype not in ("movie", "tvshow", "episode", "season"):
            if self._last_item_key:
                self._clear_properties()
                self._last_item_key = None
                self._last_prop_keys = set()
            return

        tvshowid_for_schedule = 0
        if dbtype == "season":
            imdb_id, tmdb_id = resolve_season_ids(dbid)
            effective_type = "tvshow"
        else:
            imdb_id, tmdb_id = resolve_ids_from(dbtype, dbid, "ListItem", SKININFO_PREFIX_MAP)
            effective_type = dbtype
            if dbtype == "tvshow":
                try:
                    tvshowid_for_schedule = int(dbid)
                except (ValueError, TypeError):
                    tvshowid_for_schedule = 0

        if not imdb_id and not tmdb_id:
            return

        cache_key = make_cache_key(effective_type, imdb_id, tmdb_id)
        if not cache_key:
            return

        cached_props = get_cached_online_properties(cache_key)

        if cache_key == self._last_item_key and cached_props:
            return

        self._last_item_key = cache_key

        if cached_props:
            props_to_set = {}
            new_keys = set()
            for key, value in cached_props.items():
                if value:
                    props_to_set[f"{ONLINE_PROPERTY_PREFIX}{key}"] = str(value)
                    new_keys.add(key)
            with self._keys_lock:
                stale_keys = self._last_prop_keys - new_keys
                self._last_prop_keys = new_keys
            for old_key in stale_keys:
                props_to_set[f"{ONLINE_PROPERTY_PREFIX}{old_key}"] = ""
            batch_set_props(props_to_set)
            return

        # New item with no cache yet: clear the previous item's props so stale data doesn't
        # linger while the fetch runs.
        if self._last_prop_keys:
            self._clear_properties()
            with self._keys_lock:
                self._last_prop_keys = set()

        if (self._fetch_thread and self._fetch_thread.is_alive()
                and self._fetch_for_key == cache_key):
            return

        if cache_key in self._service.updater_in_progress:
            return

        self._fetch_for_key = cache_key
        self._fetch_thread = threading.Thread(
            target=self._fetch_worker,
            args=(effective_type, imdb_id, tmdb_id, cache_key, tvshowid_for_schedule),
            daemon=True,
        )
        self._fetch_thread.start()

    def _fetch_worker(self, media_type: str, imdb_id: str, tmdb_id: str,
                      cache_key: str, tvshowid_for_schedule: int = 0) -> None:
        try:
            abort_flag = self._service.capped_abort_flag
            if abort_flag.is_requested():
                return

            props = fetch_all_online_data(media_type, imdb_id, tmdb_id, abort_flag)

            if abort_flag.is_requested():
                return
            if not props:
                return

            ttl_hours = get_online_ttl(media_type, tmdb_id)
            cache_online_properties(cache_key, props, ttl_hours=ttl_hours)

            if media_type == "tvshow" and tvshowid_for_schedule:
                self._upsert_schedule_from_cache(tmdb_id, tvshowid_for_schedule)

            if cache_key != self._last_item_key:
                return

            props_to_set = {}
            new_keys = set()
            for key, value in props.items():
                if value:
                    props_to_set[f"{ONLINE_PROPERTY_PREFIX}{key}"] = str(value)
                    new_keys.add(key)

            with self._keys_lock:
                stale_keys = self._last_prop_keys - new_keys
                self._last_prop_keys = new_keys
            for old_key in stale_keys:
                props_to_set[f"{ONLINE_PROPERTY_PREFIX}{old_key}"] = ""

            batch_set_props(props_to_set)

        except Exception as e:
            log("Service", f"Online fetch error: {e}", xbmc.LOGWARNING)

    @staticmethod
    def _upsert_schedule_from_cache(tmdb_id: str, tvshowid: int) -> None:
        """Populate `tv_schedule` from cached TMDB metadata after a successful tvshow fetch."""
        tmdb_data = get_cached_metadata("tvshow", tmdb_id)
        if not tmdb_data:
            return
        today = datetime.now().strftime("%Y-%m-%d")
        next_ep = tmdb_data.get("next_episode_to_air")
        if next_ep and (next_ep.get("air_date") or "") < today:
            next_ep = None
        upsert_schedule(
            tmdb_id, tvshowid, tmdb_data.get("name") or "",
            tmdb_data.get("status") or "",
            next_ep,
            tmdb_data.get("last_episode_to_air"),
        )

    def _clear_properties(self) -> None:
        clear_group(ONLINE_PROPERTY_PREFIX)
