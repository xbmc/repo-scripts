"""Independent IMDb Top 250 auto-update service thread."""
from __future__ import annotations

import threading
import time
from typing import Final

import xbmc

from lib.infrastructure import tasks as task_manager
from lib.kodi.client import ADDON, log
from lib.kodi.utilities import setting_float


TOP250_CHECK_INTERVAL: Final = 86400  # Trakt rebuilds the list once a day
TOP250_RECHECK_MARGIN: Final = 3600
_BACKOFF_SECONDS = (3600, 14400, 86400)  # 1h, 4h, 24h after consecutive fetch failures


class Top250UpdateMonitor(xbmc.Monitor):
    """Monitor for library scan notifications to trigger a Top 250 pass."""

    def __init__(self, service: 'Top250UpdateService'):
        super().__init__()
        self._service = service

    def onNotification(self, sender: str, method: str, data: str) -> None:
        """Trigger a Top 250 pass on `VideoLibrary.OnScanFinished`."""
        _ = sender, data
        if method == 'VideoLibrary.OnScanFinished':
            self._service.on_library_scan_finished()


class Top250UpdateService(threading.Thread):
    """Background Top 250 updater, checking an hour after Trakt's daily list rebuild."""

    def __init__(self):
        super().__init__(daemon=True)
        self.abort = threading.Event()
        self._update_lock = threading.Lock()
        self._consecutive_failures = 0
        self._next_retry_at = 0.0

    def run(self) -> None:
        """Service thread entry. Polls every 5s, fires the Top 250 pass when one is due."""
        monitor = Top250UpdateMonitor(self)
        log("Service", "Top 250 auto-update service started", xbmc.LOGINFO)

        while not monitor.waitForAbort(5):
            if self.abort.is_set():
                break

            if ADDON.getSetting("top250_auto_update") not in ("daily", "both"):
                continue

            now = time.time()
            if now < self._next_retry_at:
                continue
            if now >= setting_float("top250_next_check"):
                self._run_update(monitor)

        log("Service", "Top 250 auto-update service stopped", xbmc.LOGINFO)

    def on_library_scan_finished(self) -> None:
        """Run a pass after a library scan when the setting asks for one."""
        if ADDON.getSetting("top250_auto_update") in ("library_scan", "both"):
            threading.Thread(
                target=self._run_update,
                args=(xbmc.Monitor(),),
                daemon=True,
            ).start()

    def _run_update(self, monitor: xbmc.Monitor) -> None:
        """Run one pass, unless a task is already registered or a pass is in flight."""
        if task_manager.is_task_running():
            log("Service", "Top 250 update deferred: another task is running", xbmc.LOGDEBUG)
            return
        if not self._update_lock.acquire(blocking=False):
            log("Service", "Top 250 update already in progress, skipping", xbmc.LOGDEBUG)
            return
        try:
            self._pass(monitor)
        except Exception as e:
            log("Service", f"Top 250 update failed: {e}", xbmc.LOGWARNING)
        finally:
            self._update_lock.release()

    def _pass(self, monitor: xbmc.Monitor) -> None:
        """Fetch the list, then write to the library only when its contents moved."""
        from lib.infrastructure.dialogs import ProgressDialog, notify_when_idle
        from lib.infrastructure.tasks import ShutdownAbortFlag
        from lib.rating.top250 import apply_updates, compute_updates, fetch_ranks

        ranks = fetch_ranks(abort_flag=ShutdownAbortFlag())
        if ranks is None:
            self._back_off()
            return

        self._consecutive_failures = 0
        self._next_retry_at = 0.0
        self._schedule_next(ranks.rebuilt_at)

        if ranks.digest == ADDON.getSetting("top250_content_hash"):
            log("Service", "Top 250 list unchanged, skipping library pass", xbmc.LOGDEBUG)
            return

        computed = compute_updates(ranks)
        if computed is None:
            return

        updates, already_correct = computed
        if not updates:
            ADDON.setSetting("top250_content_hash", ranks.digest)
            return

        with ProgressDialog(use_background=True,
                            heading=ADDON.getLocalizedString(32600)) as progress:
            progress.create(ADDON.getLocalizedString(32603))
            stats = apply_updates(updates, already_correct, progress)

        if stats.cancelled:
            return

        ADDON.setSetting("top250_content_hash", ranks.digest)
        notify_when_idle(
            ADDON.getLocalizedString(32605),
            ADDON.getLocalizedString(32606).format(
                stats.updated, stats.cleared, stats.already_correct),
            monitor,
            self.abort,
        )

    def _schedule_next(self, rebuilt_at: float) -> None:
        """Aim the next check an hour past the rebuild that follows the one just observed."""
        target = (rebuilt_at or time.time()) + TOP250_CHECK_INTERVAL + TOP250_RECHECK_MARGIN
        now = time.time()
        while target <= now:
            target += TOP250_CHECK_INTERVAL
        ADDON.setSetting("top250_next_check", str(target))

    def _back_off(self) -> None:
        """Push the next attempt out after a failed fetch."""
        idx = min(self._consecutive_failures, len(_BACKOFF_SECONDS) - 1)
        backoff = _BACKOFF_SECONDS[idx]
        self._consecutive_failures += 1
        self._next_retry_at = time.time() + backoff
        log(
            "Service",
            f"Top 250 fetch failed; retry in {backoff}s "
            f"(failure #{self._consecutive_failures})",
            xbmc.LOGWARNING,
        )
