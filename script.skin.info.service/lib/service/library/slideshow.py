"""Slideshow pool population + property update integration."""
from __future__ import annotations

import threading
import time
from typing import Optional

import xbmc

from lib.kodi.client import log

# Idle catch-all reconcile: runs at most once per interval, only after the box has been idle a
# while - catches fanart changed outside our feature or a scan (Kodi GUI chooser, other apps).
_RECONCILE_INTERVAL_S = 21600  # 6h
_RECONCILE_IDLE_S = 60


class SlideshowDriver:
    """Drives slideshow pool population (first run) and periodic property refresh."""

    def __init__(self):
        self._pool_populated = False
        self._last_update = 0.0
        self._update_thread: Optional[threading.Thread] = None
        self._stopping = False
        self._last_reconcile = 0.0
        self._reconcile_thread: Optional[threading.Thread] = None
        from lib.service.slideshow import PlaylistRotator, LibrarySlideshow
        self._library = LibrarySlideshow()
        self._playlists = PlaylistRotator()

    def invalidate_playlists(self) -> None:
        """Force playlist-background slots to re-fetch on the next tick (library changed)."""
        self._playlists.invalidate()

    def populate_pool_if_needed(self) -> None:
        """First-run pool population. Subsequent calls are no-ops."""
        if self._pool_populated:
            return

        try:
            from lib.service.slideshow import is_pool_populated, populate_slideshow_pool

            if not is_pool_populated():
                log("Service", "Slideshow: Populating pool for first time...", xbmc.LOGINFO)
                populate_slideshow_pool()
                log("Service", "Slideshow: Pool population complete", xbmc.LOGINFO)

            self._pool_populated = True
        except Exception as e:
            log("Service", f"Slideshow: Error populating pool: {str(e)}", xbmc.LOGERROR)

    def update(self) -> None:
        """Refresh slideshow props if the skin opted in and the interval has elapsed."""
        if not xbmc.getCondVisibility('Skin.HasSetting(SkinInfo.EnableSlideshow)'):
            return

        interval_str = xbmc.getInfoLabel('Skin.String(SkinInfo.SlideshowRefreshInterval)') or '10'
        try:
            from lib.service.slideshow import MIN_SLIDESHOW_INTERVAL, MAX_SLIDESHOW_INTERVAL
            interval = int(interval_str)
            interval = max(MIN_SLIDESHOW_INTERVAL, min(interval, MAX_SLIDESHOW_INTERVAL))
        except ValueError:
            interval = 10

        now = time.time()
        if (now - self._last_update) < interval:
            return

        # runs on a thread: force-caching fanart does blocking xbmcvfs reads
        # that would stall the 100ms service loop
        if self._update_thread and self._update_thread.is_alive():
            return
        self._update_thread = threading.Thread(target=self._run_update, daemon=True)
        self._update_thread.start()

    def _run_update(self) -> None:
        try:
            if self._stopping:
                return
            self._library.refresh()
            self._playlists.refresh()
            self._last_update = time.time()
        except Exception as e:
            log("Service", f"Slideshow: Update error: {str(e)}", xbmc.LOGERROR)

    def reconcile_if_idle(self) -> None:
        """Idle-gated periodic full reconcile - catches art changed outside our feature or a scan.

        Runs at most once per interval, only when the box has been idle and the slideshow is in
        use. The reconcile diffs the pool against the library and no-ops when nothing changed.
        """
        if not xbmc.getCondVisibility('Skin.HasSetting(SkinInfo.EnableSlideshow)'):
            return
        if (time.time() - self._last_reconcile) < _RECONCILE_INTERVAL_S:
            return
        # skip during video playback: idle climbs mid-movie, but a background library read can
        # stutter low-power devices. music playback is fine. retries once video stops + idle.
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
        try:
            if self._stopping:
                return
            from lib.service.slideshow import reconcile_pool
            reconcile_pool(('movie', 'tvshow', 'artist'))
        except Exception as e:
            log("Service", f"Slideshow: Reconcile error: {str(e)}", xbmc.LOGERROR)

    def cleanup(self) -> None:
        """Clear `SkinInfo.Slideshow.*` window properties.

        Waits briefly for an in-flight update so it can't re-set props after the clear.
        """
        try:
            self._stopping = True
            for thread in (self._update_thread, self._reconcile_thread):
                if thread and thread.is_alive():
                    thread.join(timeout=5)
            self._library.clear()
            self._playlists.clear()
        except Exception as e:
            log("Service", f"Slideshow: Cleanup error: {str(e)}", xbmc.LOGERROR)
