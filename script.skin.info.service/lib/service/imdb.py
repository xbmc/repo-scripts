"""Independent IMDb dataset auto-update service thread."""
from __future__ import annotations

import threading
import time
from typing import Final

import xbmc

from lib.infrastructure import tasks as task_manager
from lib.kodi.client import ADDON, log
from lib.kodi.utilities import setting_float


IMDB_CHECK_INTERVAL: Final = 86400  # 24 hours
_BACKOFF_SECONDS = (3600, 14400, 86400)  # 1h, 4h, 24h after consecutive refresh failures
_SCOPE_TYPES: Final = {
    "all": ("movie", "tvshow", "episode"),
    "movies_tvshows": ("movie", "tvshow"),
    "movies": ("movie",),
}


def _scope_types() -> tuple:
    """Media types the auto-update scope setting covers."""
    scope = ADDON.getSetting("imdb_auto_update_scope") or "movies_tvshows"
    return _SCOPE_TYPES.get(scope, _SCOPE_TYPES["movies_tvshows"])


class ImdbUpdateMonitor(xbmc.Monitor):
    """Monitor for library scan notifications to trigger IMDb dataset refresh."""

    def __init__(self, service: 'ImdbUpdateService'):
        super().__init__()
        self._service = service

    def onNotification(self, sender: str, method: str, data: str) -> None:
        """Trigger IMDb refresh on `VideoLibrary.OnScanFinished`."""
        _ = sender, data
        if method == 'VideoLibrary.OnScanFinished':
            self._service._on_library_scan_finished()


class ImdbUpdateService(threading.Thread):
    """Background IMDb rating updater, run daily or after a library scan as the setting chooses."""

    def __init__(self):
        super().__init__(daemon=True)
        self.abort = threading.Event()
        self._update_lock = threading.Lock()
        self._consecutive_failures = 0
        self._next_retry_at = 0.0

    def _set_last_check(self) -> None:
        """Stamp the daily check time in the settings."""
        ADDON.setSetting("imdb_last_auto_check", str(time.time()))

    def run(self) -> None:
        """Service thread entry. Polls every 5s, fires daily IMDb dataset refresh."""
        monitor = ImdbUpdateMonitor(self)
        log("Service", "IMDb auto-update service started", xbmc.LOGINFO)

        while not monitor.waitForAbort(5):
            if self.abort.is_set():
                break

            setting = ADDON.getSetting("imdb_auto_update")
            if setting in ("when_updated", "both"):
                now = time.time()
                if now < self._next_retry_at:
                    continue
                if (now - setting_float("imdb_last_auto_check")) >= IMDB_CHECK_INTERVAL:
                    if self._run_update(monitor):
                        self._set_last_check()

        log("Service", "IMDb auto-update service stopped", xbmc.LOGINFO)

    def _on_library_scan_finished(self) -> None:
        """Start an IMDb update after a library scan when the setting asks for it."""
        setting = ADDON.getSetting("imdb_auto_update")
        if setting in ("library_scan", "both"):
            threading.Thread(
                target=self._run_update,
                args=(xbmc.Monitor(),),
                daemon=True,
            ).start()

    def _run_update(self, monitor: xbmc.Monitor) -> bool:
        """Run one pass; True when the daily check may advance, False on a collision or failure."""
        if task_manager.is_task_running():
            log("Service", "IMDb update deferred: another task is running", xbmc.LOGDEBUG)
            return False
        if not self._update_lock.acquire(blocking=False):
            log("Service", "IMDb update already in progress, skipping", xbmc.LOGDEBUG)
            return False
        try:
            from lib.data.api.imdb import RefreshResult, get_imdb_dataset
            from lib.data.database import workflow as db

            dataset = get_imdb_dataset()
            abort_flag = task_manager.ServiceAbortFlag(self.abort)
            if dataset.refresh_if_stale(abort_flag) == RefreshResult.Failed:
                idx = min(self._consecutive_failures, len(_BACKOFF_SECONDS) - 1)
                backoff = _BACKOFF_SECONDS[idx]
                self._consecutive_failures += 1
                self._next_retry_at = time.time() + backoff
                log(
                    "Service",
                    f"IMDb dataset refresh failed; retry in {backoff}s "
                    f"(failure #{self._consecutive_failures})",
                    xbmc.LOGWARNING,
                )
                return False

            self._consecutive_failures = 0
            self._next_retry_at = 0.0

            if not db.has_synced_ratings():
                self._run_full_update()
            else:
                self._run_incremental(monitor)
        except Exception as e:
            log("Service", f"IMDb update failed: {e}", xbmc.LOGWARNING)
        finally:
            self._update_lock.release()
        return True

    def _run_incremental(self, monitor: xbmc.Monitor) -> None:
        """Update only the IMDb ratings that changed, notifying when any moved."""
        from lib.infrastructure.dialogs import notify_when_idle
        from lib.rating.imdb import update_changed_imdb_ratings

        updated = 0
        for media_type in _scope_types():
            if monitor.abortRequested() or self.abort.is_set():
                return
            updated += update_changed_imdb_ratings(media_type, monitor).get("updated", 0)
        if updated > 0:
            message = ADDON.getLocalizedString(32319).format(updated)
        else:
            message = ADDON.getLocalizedString(32320)
        notify_when_idle(ADDON.getLocalizedString(32318), message, monitor, self.abort)

    def _run_full_update(self) -> None:
        """Run the IMDb rating update across whichever media the scope setting names."""
        from lib.rating.updater import update_library_ratings

        media_types = _scope_types()
        log("Service", f"Starting IMDb full auto-update ({', '.join(media_types)})", xbmc.LOGINFO)
        for media_type in media_types:
            update_library_ratings(media_type, [], use_background=True, source_mode="imdb",
                                   gated=True)
