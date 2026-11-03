"""Focus handler: monitors ListItem changes and sets `SkinInfo.Online.*` properties."""
from __future__ import annotations

import threading
import time
from typing import Dict, Optional, Set, Tuple, TYPE_CHECKING, Final

import xbmc

from lib.kodi.client import log
from lib.kodi.utilities import (
    LabelSnapshot, clear_group, batch_set_props, modal_dialog_active, normalize_dbtype,
)
from lib.data.database.cache import (
    CacheKey,
    get_cached_online_properties_state,
    online_cache_generation,
    cache_online_properties,
)
from lib.data.online import (
    apply_derived_props, fetch_all_online_data, get_online_ttl, make_cache_key,
    show_scoped_props,
)
from lib.service.online.helpers import (
    infolabel_imdb_id,
    resolve_ids_from,
    resolve_show_ids,
    unlisted_ids,
)
from lib.service.online.fetchers import EpisodeRatings

if TYPE_CHECKING:
    from lib.service.online.main import OnlineServiceMain


ONLINE_PROPERTY_PREFIX: Final = "SkinInfo.Online."
FOCUS_LABELS: Final = (
    "ListItem.DBID", "ListItem.DBType", "ListItem.FileNameAndPath", "ListItem.Label",
    "ListItem.Season", "ListItem.Episode", "ListItem.TvShowDBID", "ListItem.UniqueID(imdb)",
    "ListItem.IMDBNumber", "ListItem.UniqueID(tmdb)", "ListItem.Property(tmdb_id)",
    "ListItem.UniqueID(tvshow.imdb)", "ListItem.Property(tvshow.imdb_id)",
    "ListItem.UniqueID(tvshow.tmdb)", "ListItem.Property(tvshow.tmdb_id)",
    "ListItem.Title", "ListItem.TVShowTitle", "ListItem.Year",
)

# a fetch that came back empty must not respawn a worker on the next tick
FETCH_BACKOFF_S: Final = 300
TITLE_RETRY_S: Final = 60
_MAX_TITLES: Final = 2000


class FocusHandler:
    """Focus tracker for movies and shows, in the library or not, applying their online props."""

    def __init__(self, service: 'OnlineServiceMain'):
        self._service = service
        self._last_item_key: Optional[CacheKey] = None
        self._last_scoped = False
        self._last_item_id: Optional[str] = None
        self._last_expires_at: int = 0
        self._last_generation: int = -1
        # guarded by _keys_lock: read+swapped from both the poll thread and fetch workers
        self._last_prop_keys: Set[str] = set()
        self._keys_lock = threading.Lock()
        self._fetch_thread: Optional[threading.Thread] = None
        self._fetch_for_key: Optional[CacheKey] = None
        self._refreshed_for_key: Optional[CacheKey] = None
        self._empty_for_key: Optional[CacheKey] = None
        self._empty_at: float = 0.0
        self._empty_generation: int = -1
        self._episode = EpisodeRatings(ONLINE_PROPERTY_PREFIX, service.capped_abort_flag)
        # (media type, title, year) -> TMDB id, or None when TMDB answered with no clear match
        self._title_ids: Dict[Tuple[str, str, int], Optional[str]] = {}
        self._title_failed: Dict[Tuple[str, str, int], float] = {}
        self._title_thread: Optional[threading.Thread] = None
        self._no_data_item: Optional[str] = None

    def process(self, labels: LabelSnapshot) -> None:
        """Read the focused item; set cached props or start a fetch, and library episode ratings."""
        dbid = labels.get("ListItem.DBID")
        dbtype = normalize_dbtype(labels.get("ListItem.DBType"))

        if dbtype not in ("movie", "tvshow", "episode", "season"):
            self._leave_item()
            return
        path = "" if dbid else labels.get("ListItem.FileNameAndPath")
        if path.startswith("pvr://"):
            self._leave_item()
            return

        if dbtype != "episode" or not dbid:
            self._episode.reset()

        item_id = f"{dbtype}:{dbid or path or labels.get('ListItem.Label')}"
        if item_id == self._no_data_item:
            return
        generation = online_cache_generation()
        if (item_id == self._last_item_id and generation == self._last_generation
                and time.time() < self._last_expires_at):
            return

        scoped = dbtype in ("season", "episode")
        effective_type = "tvshow" if scoped else dbtype
        if not dbid:
            imdb_id, tmdb_id = unlisted_ids(scoped, labels.get)
            if not imdb_id and not tmdb_id:
                title_id = self._title_id(effective_type, scoped, labels)
                if title_id is None:
                    self._leave_item()
                    return
                tmdb_id = title_id
        elif scoped:
            imdb_id, tmdb_id = resolve_show_ids(dbtype, dbid, "ListItem", labels.get)
        else:
            imdb_id, tmdb_id = resolve_ids_from(dbtype, dbid, "ListItem", labels.get)

        if not imdb_id and not tmdb_id:
            if not dbid:
                self._leave_item()
                self._no_data_item = item_id
            return

        if dbtype == "episode" and dbid:
            self._episode.update(
                dbid, labels.get("ListItem.Season"), labels.get("ListItem.Episode"),
                infolabel_imdb_id("ListItem", labels.get), imdb_id, tmdb_id)

        cache_key = make_cache_key(effective_type, imdb_id, tmdb_id)
        if not cache_key:
            return

        cached_props, expires_at = get_cached_online_properties_state(cache_key)
        expired = expires_at <= time.time()

        # id resolution lags the focus; the key can still be the previous item's
        self._last_item_id = None
        self._last_expires_at = 0
        if cache_key != self._refreshed_for_key:
            self._refreshed_for_key = None

        if (cache_key == self._last_item_key and scoped == self._last_scoped
                and cached_props and not expired):
            return

        self._last_item_key = cache_key
        self._last_scoped = scoped

        if cached_props:
            self._publish(apply_derived_props(dict(cached_props), effective_type, imdb_id,
                                              tmdb_id))

            if not expired:
                self._last_item_id = item_id
                self._last_generation = generation
                self._last_expires_at = expires_at
                return
            # row stays expired until the fetch writes it back
            if cache_key == self._refreshed_for_key:
                return
            self._refreshed_for_key = cache_key

        # props persist across items
        elif self._last_prop_keys:
            self._clear_properties()
            with self._keys_lock:
                self._last_prop_keys = set()

        if (self._fetch_thread and self._fetch_thread.is_alive()
                and self._fetch_for_key == cache_key):
            return

        if generation != self._empty_generation:
            self._empty_for_key = None
        if (cache_key == self._empty_for_key
                and time.time() - self._empty_at < FETCH_BACKOFF_S):
            return

        if cache_key in self._service.updater_in_progress:
            return

        self._fetch_for_key = cache_key
        self._fetch_thread = threading.Thread(
            target=self._fetch_worker,
            args=(effective_type, imdb_id, tmdb_id, cache_key, bool(dbid)),
            daemon=True,
        )
        self._fetch_thread.start()

    def _fetch_worker(self, media_type: str, imdb_id: str, tmdb_id: str,
                      cache_key: CacheKey, library: bool) -> None:
        """Fetch and cache online data for a focused item, publishing it only if focus holds."""
        try:
            abort_flag = self._service.capped_abort_flag
            if abort_flag.is_requested():
                return

            props = fetch_all_online_data(media_type, imdb_id, tmdb_id, abort_flag,
                                          is_library_item=library)

            if abort_flag.is_requested():
                return
            if not props:
                self._empty_for_key = cache_key
                self._empty_at = time.time()
                self._empty_generation = online_cache_generation()
                if cache_key == self._refreshed_for_key:
                    self._refreshed_for_key = None
                return

            ttl_hours = get_online_ttl(media_type, tmdb_id)
            cache_online_properties(cache_key, props, ttl_hours=ttl_hours)

            if cache_key != self._last_item_key:
                return

            self._publish(props)

        except Exception as e:
            log("Service", f"Online fetch error: {e}", xbmc.LOGWARNING)

    def _leave_item(self) -> None:
        """Clear the last item's props, kept while a modal dialog is open."""
        if modal_dialog_active():
            return
        if self._last_item_key:
            self._clear_properties()
            self._last_item_key = None
            self._last_item_id = None
            self._last_expires_at = 0
            self._last_generation = -1
            with self._keys_lock:
                self._last_prop_keys = set()
            self._empty_for_key = None

    def _title_id(self, media_type: str, scoped: bool, labels: LabelSnapshot) -> Optional[str]:
        """Resolve the item's TMDB id by title; empty for none, None while a search is due."""
        title = labels.get("ListItem.TVShowTitle" if scoped else "ListItem.Title")
        year = labels.get("ListItem.Year")
        key = (media_type, title, int(year) if year.isdigit() and not scoped else 0)
        if not title:
            return ""
        if key in self._title_ids:
            return self._title_ids[key] or ""
        if self._title_thread and self._title_thread.is_alive():
            return None
        if time.time() - self._title_failed.get(key, 0.0) < TITLE_RETRY_S:
            return None
        self._title_thread = threading.Thread(target=self._title_worker, args=(key,), daemon=True)
        self._title_thread.start()
        return None

    def _title_worker(self, key: Tuple[str, str, int]) -> None:
        """Search TMDB for a title, keeping its id or that nothing fits, or the time it failed."""
        from lib.data.pvr import match_title
        try:
            found = match_title(key[1], key[2], key[0], self._service.capped_abort_flag)
        except Exception as e:
            log("Service", f"Online title search failed for '{key[1]}': {e}", xbmc.LOGDEBUG)
            self._title_failed[key] = time.time()
            return
        if len(self._title_ids) >= _MAX_TITLES:
            self._title_ids.clear()
        self._title_ids[key] = str(found) if found else None

    def _publish(self, props: dict) -> None:
        """Publish the item's props, its show's ratings under `TVShow.` on a season or episode."""
        if self._last_scoped:
            props = show_scoped_props(props)
        props_to_set: Dict[str, Optional[str]] = {
            f"{ONLINE_PROPERTY_PREFIX}{k}": str(v) for k, v in props.items() if v}
        new_keys = {k for k, v in props.items() if v}
        with self._keys_lock:
            stale_keys = self._last_prop_keys - new_keys - self._episode.owned()
            self._last_prop_keys = new_keys
        for old_key in stale_keys:
            props_to_set[f"{ONLINE_PROPERTY_PREFIX}{old_key}"] = ""
        batch_set_props(props_to_set)

    def _clear_properties(self) -> None:
        """Clear every `SkinInfo.Online.*` property."""
        clear_group(ONLINE_PROPERTY_PREFIX)
        self._episode.forget()
