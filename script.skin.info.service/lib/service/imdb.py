"""Independent IMDb dataset auto-update service thread."""
from __future__ import annotations

import threading
import time

import xbmc

from lib.infrastructure import tasks as task_manager
from lib.kodi.client import ADDON, log


IMDB_CHECK_INTERVAL = 86400  # 24 hours
_BACKOFF_SECONDS = (3600, 14400, 86400)  # 1h, 4h, 24h after consecutive refresh failures


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
    """Auto-updates IMDb ratings. Gated by `imdb_auto_update` setting only.

    Runs periodic dataset checks and reacts to `VideoLibrary.OnScanFinished`.
    """

    def __init__(self):
        super().__init__(daemon=True)
        self.abort = threading.Event()
        self._update_lock = threading.Lock()
        self._consecutive_failures = 0
        self._next_retry_at = 0.0

    def _get_last_check(self) -> float:
        stored = ADDON.getSetting("imdb_last_auto_check")
        if stored:
            try:
                return float(stored)
            except (ValueError, TypeError):
                pass
        return 0.0

    def _set_last_check(self) -> None:
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
                if (now - self._get_last_check()) >= IMDB_CHECK_INTERVAL:
                    if self._run_update(monitor):
                        self._set_last_check()

        log("Service", "IMDb auto-update service stopped", xbmc.LOGINFO)

    def _on_library_scan_finished(self) -> None:
        setting = ADDON.getSetting("imdb_auto_update")
        if setting in ("library_scan", "both"):
            threading.Thread(
                target=self._run_update,
                args=(xbmc.Monitor(),),
                daemon=True,
            ).start()

    def _run_update(self, monitor: xbmc.Monitor) -> bool:
        """Returns True if the daily-check timestamp should advance, False otherwise.

        Returns False on collision (another task running) or transient dataset-refresh
        failures; in the failure case `_next_retry_at` is set so the run loop backs off
        (1h, 4h, then 24h) instead of hammering on every 5s tick.
        """
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
            if dataset.refresh_if_stale() == RefreshResult.Failed:
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

            if db.get_synced_items_count() == 0:
                self._run_full_update()
            else:
                self._run_incremental(monitor)
        except Exception as e:
            log("Service", f"IMDb update failed: {e}", xbmc.LOGWARNING)
        finally:
            self._update_lock.release()
        return True

    def _run_incremental(self, monitor: xbmc.Monitor) -> None:
        from lib.rating.imdb import update_changed_imdb_ratings

        stats = update_changed_imdb_ratings(monitor=monitor)
        updated = stats.get("updated", 0)
        if updated > 0:
            message = ADDON.getLocalizedString(32319).format(updated)
        else:
            message = ADDON.getLocalizedString(32320)
        self._notify_when_idle(
            ADDON.getLocalizedString(32318),
            message,
            monitor,
        )

    def _run_full_update(self) -> None:
        from lib.rating.updater import update_library_ratings

        scope = ADDON.getSetting("imdb_auto_update_scope") or "movies_tvshows"
        log("Service", f"Starting IMDb full auto-update (scope={scope})", xbmc.LOGINFO)

        if scope in ("all", "movies_tvshows", "movies"):
            update_library_ratings("movie", [], use_background=True, source_mode="imdb")
        if scope in ("all", "movies_tvshows"):
            update_library_ratings("tvshow", [], use_background=True, source_mode="imdb")
        if scope == "all":
            update_library_ratings("episode", [], use_background=True, source_mode="imdb")

    def _notify_when_idle(
        self,
        heading: str,
        message: str,
        monitor: xbmc.Monitor,
    ) -> None:
        """Show notification, deferring until playback stops."""
        while xbmc.getCondVisibility("Player.HasVideo"):
            if monitor.waitForAbort(30):
                return
            if self.abort.is_set():
                return

        from lib.infrastructure.dialogs import show_notification
        show_notification(heading, message)
