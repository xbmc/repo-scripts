"""Video player handler: sets `SkinInfo.Player.Online.*` props for the playing movie/episode."""
from __future__ import annotations

import threading
import time
from typing import Dict, Optional, Tuple, TYPE_CHECKING, Final

import xbmc

from lib.kodi.client import log
from lib.kodi.utilities import clear_group, batch_set_props
from lib.data.database.cache import CacheKey
from lib.data.online import fetch_all_online_data, make_cache_key, show_scoped_props
from lib.service.online.helpers import (
    infolabel_imdb_id,
    resolve_ids_from,
    resolve_show_ids,
)
from lib.service.online.fetchers import EpisodeRatings

if TYPE_CHECKING:
    from lib.service.online.main import OnlineServiceMain


PLAYER_ONLINE_PROPERTY_PREFIX: Final = "SkinInfo.Player.Online."

# a fetch that came back empty must not respawn a worker on the next tick
FETCH_BACKOFF_S: Final = 300


class PlayerHandler:
    """Tracks the playing movie/episode and applies fetched online properties (no cache)."""

    def __init__(self, service: 'OnlineServiceMain'):
        self._service = service
        self._last_key: Optional[CacheKey] = None
        self._player = xbmc.Player()
        self._type_key: Optional[Tuple[str, str]] = None
        self._type = ""
        self._fetch_thread: Optional[threading.Thread] = None
        self._fetch_for_key: Optional[CacheKey] = None
        self._empty_for_key: Optional[CacheKey] = None
        self._empty_at: float = 0.0
        self._episode = EpisodeRatings(PLAYER_ONLINE_PROPERTY_PREFIX, service.capped_abort_flag)

    def process(self) -> None:
        """Read VideoPlayer state; fetch and apply online props for movies/episodes."""
        if not self._player.isPlayingVideo():
            self._clear_if_active()
            return

        dbid = xbmc.getInfoLabel("VideoPlayer.DBID") or ""
        if not dbid:
            self._clear_if_active()
            return

        key = (dbid, xbmc.getInfoLabel("Player.Filenameandpath"))
        if key != self._type_key:
            self._type_key = key
            if xbmc.getCondVisibility("VideoPlayer.Content(movies)"):
                self._type = "movie"
            elif xbmc.getCondVisibility("VideoPlayer.Content(episodes)"):
                self._type = "episode"
            else:
                self._type = ""
        dbtype = self._type
        if not dbtype:
            self._clear_if_active()
            return

        if dbtype == "episode":
            imdb_id, tmdb_id = resolve_show_ids(dbtype, dbid, "VideoPlayer")
        else:
            imdb_id, tmdb_id = resolve_ids_from(dbtype, dbid, "VideoPlayer")
            self._episode.reset()

        if not imdb_id and not tmdb_id:
            self._clear_if_active()
            return

        if dbtype == "episode":
            self._episode.update(
                dbid, xbmc.getInfoLabel("VideoPlayer.Season"),
                xbmc.getInfoLabel("VideoPlayer.Episode"),
                infolabel_imdb_id("VideoPlayer"), imdb_id, tmdb_id)
            dbtype = "tvshow"

        cache_key = make_cache_key(dbtype, imdb_id, tmdb_id, "player")
        if not cache_key:
            return

        if cache_key == self._last_key:
            return
        if self._last_key:
            clear_group(PLAYER_ONLINE_PROPERTY_PREFIX)
            self._episode.forget()
            self._last_key = None

        if (self._fetch_thread and self._fetch_thread.is_alive()
                and self._fetch_for_key == cache_key):
            return

        if (cache_key == self._empty_for_key
                and time.time() - self._empty_at < FETCH_BACKOFF_S):
            return

        self._fetch_for_key = cache_key
        self._fetch_thread = threading.Thread(
            target=self._fetch_worker,
            args=(dbtype, imdb_id, tmdb_id, cache_key),
            daemon=True,
        )
        self._fetch_thread.start()

    def _fetch_worker(self, media_type: str, imdb_id: str, tmdb_id: str,
                      cache_key: CacheKey) -> None:
        """Fetch online data for the playing item, discarding it if playback has moved on."""
        try:
            abort_flag = self._service.capped_abort_flag
            if abort_flag.is_requested():
                return

            props = fetch_all_online_data(media_type, imdb_id, tmdb_id, abort_flag)

            if abort_flag.is_requested():
                return
            if not props:
                self._empty_for_key = cache_key
                self._empty_at = time.time()
                return
            if cache_key != self._fetch_for_key:
                return
            # a show here is always the playing episode's
            if media_type == "tvshow":
                props = show_scoped_props(props)

            props_to_set: Dict[str, Optional[str]] = {
                f"{PLAYER_ONLINE_PROPERTY_PREFIX}{k}": str(v)
                for k, v in props.items() if v
            }
            batch_set_props(props_to_set)
            self._last_key = cache_key

        except Exception as e:
            log("Service", f"Online player fetch error: {e}", xbmc.LOGWARNING)

    def _clear_if_active(self) -> None:
        """Clear the player's online properties if any are still set."""
        if self._last_key:
            clear_group(PLAYER_ONLINE_PROPERTY_PREFIX)
            self._last_key = None
        self._episode.reset()
        self._empty_for_key = None
