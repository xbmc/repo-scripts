"""Slideshow pool population + property update integration."""
from __future__ import annotations

import threading
import time
from typing import Optional, Tuple, Final

import xbmc

from lib.kodi.utilities import skin_bool
from lib.kodi.client import log

# idle reconcile catches fanart changed outside the add-on, such as Kodi's own art chooser
_RECONCILE_INTERVAL_S: Final = 21600  # 6h
_RECONCILE_IDLE_S: Final = 60

# shortest rotation is MIN_SLIDESHOW_INTERVAL
_SETTINGS_TTL_S: Final = 1.0


class SlideshowDriver:
    """Drives slideshow pool population (first run) and periodic property refresh."""

    def __init__(self):
        self._pool_populated = False
        self._last_update = 0.0
        self._update_thread: Optional[threading.Thread] = None
        self._stopping = False
        self._last_reconcile = 0.0
        self._reconcile_thread: Optional[threading.Thread] = None
        self._settings_read = 0.0
        self._enabled = False
        self._interval = 10
        from lib.service.slideshow import PlaylistRotator, LibrarySlideshow
        self._library = LibrarySlideshow()
        self._playlists = PlaylistRotator()
        from lib.infrastructure.tasks import ShutdownAbortFlag
        self._abort = ShutdownAbortFlag()

    def invalidate_playlists(self) -> None:
        """Force playlist-background slots to re-fetch on the next tick (library changed)."""
        self._playlists.invalidate()

    def populate_pool_if_needed(self) -> None:
        """First-run pool population. Subsequent calls are no-ops."""
        if self._pool_populated:
            return

        try:
            from lib.data.slideshow import is_pool_populated, populate_slideshow_pool

            if not is_pool_populated():
                log("Service", "Slideshow: Populating pool for first time...", xbmc.LOGINFO)
                populate_slideshow_pool()
                log("Service", "Slideshow: Pool population complete", xbmc.LOGINFO)

            self._pool_populated = True
        except Exception as e:
            log("Service", f"Slideshow: Error populating pool: {str(e)}", xbmc.LOGERROR)

    def _settings(self) -> Tuple[bool, int]:
        """Read the enable flag and refresh interval, at most once a second."""
        now = time.time()
        if (now - self._settings_read) >= _SETTINGS_TTL_S:
            self._enabled = skin_bool('SkinInfo.EnableSlideshow')
            self._interval = self._read_interval()
            self._settings_read = now
        return self._enabled, self._interval

    @staticmethod
    def _read_interval() -> int:
        """Clamp the skin's refresh interval to the supported range, defaulting to 10s."""
        from lib.service.slideshow import MIN_SLIDESHOW_INTERVAL, MAX_SLIDESHOW_INTERVAL
        raw = xbmc.getInfoLabel('Skin.String(SkinInfo.SlideshowRefreshInterval)') or '10'
        try:
            return max(MIN_SLIDESHOW_INTERVAL, min(int(raw), MAX_SLIDESHOW_INTERVAL))
        except ValueError:
            return 10

    def update(self) -> None:
        """Refresh slideshow props if the skin opted in and the interval has elapsed."""
        enabled, interval = self._settings()
        if not enabled:
            return

        now = time.time()
        if (now - self._last_update) < interval:
            return

        # force-caching fanart does blocking xbmcvfs reads
        if self._update_thread and self._update_thread.is_alive():
            return
        self._update_thread = threading.Thread(target=self._run_update, daemon=True)
        self._update_thread.start()

    def _run_update(self) -> None:
        """Refresh the library and playlist pools, unless a stop is pending."""
        try:
            if self._stopping:
                return
            self._library.refresh(self._abort)
            self._playlists.refresh(self._abort)
            self._last_update = time.time()
        except Exception as e:
            log("Service", f"Slideshow: Update error: {str(e)}", xbmc.LOGERROR)

    def reconcile_if_idle(self) -> None:
        """Reconcile the whole pool at most every 6 hours, once the box is idle and slideshow on."""
        enabled, _ = self._settings()
        if not enabled:
            return
        if (time.time() - self._last_reconcile) < _RECONCILE_INTERVAL_S:
            return
        # idle time climbs mid-movie, and a library read can stutter low-power devices
        if xbmc.Player().isPlayingVideo():
            return
        if xbmc.getGlobalIdleTime() < _RECONCILE_IDLE_S:
            return
        if self._reconcile_thread and self._reconcile_thread.is_alive():
            return
        self._last_reconcile = time.time()
        self._reconcile_thread = threading.Thread(target=self._run_reconcile, daemon=True)
        self._reconcile_thread.start()

    def _run_reconcile(self) -> None:
        """Reconcile every slideshow pool type, unless a stop is pending."""
        try:
            if self._stopping:
                return
            from lib.data.slideshow import reconcile_pool
            reconcile_pool(('movie', 'tvshow', 'artist', 'musicvideo'), self._abort)
        except Exception as e:
            log("Service", f"Slideshow: Reconcile error: {str(e)}", xbmc.LOGERROR)

    def cleanup(self) -> None:
        """Clear `SkinInfo.Slideshow.*` after stopping in-flight work and briefly waiting for it."""
        try:
            self._stopping = True
            self._abort.request()
            for name, thread in (('update', self._update_thread),
                                 ('reconcile', self._reconcile_thread)):
                if thread and thread.is_alive():
                    thread.join(timeout=5)
                    if thread.is_alive():
                        log("Service", f"Slideshow: {name} still running after cleanup",
                            xbmc.LOGWARNING)
            self._library.clear()
            self._playlists.clear()
        except Exception as e:
            log("Service", f"Slideshow: Cleanup error: {str(e)}", xbmc.LOGERROR)
