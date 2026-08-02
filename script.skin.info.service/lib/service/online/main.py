"""Online data service: coordinator thread composing focus/player/music/updater handlers."""
from __future__ import annotations

import threading
from typing import Optional

import xbmc

from lib.kodi.client import log
from lib.service.online.focus import FocusHandler
from lib.service.online.player import PlayerHandler
from lib.service.online.musicplayer import MusicPlayerHandler
from lib.service.online.musicvideo import MusicVideoFocusHandler
from lib.service.online.updater import UpdaterHandler


ONLINE_POLL_INTERVAL = 0.10

MAX_REQUEST_SECONDS = 30.0  # runaway backstop; shutdown handled by the connection watcher


class ServiceAbortFlag:
    """Abort flag for online API calls (Kodi abort + service stop).

    max_request_seconds, when set, caps each request so a read can't outlast shutdown.
    """

    def __init__(self, abort_event: threading.Event,
                 max_request_seconds: Optional[float] = None):
        self._abort_event = abort_event
        self._monitor = xbmc.Monitor()
        self.max_request_seconds = max_request_seconds

    def is_requested(self) -> bool:
        """True if the service or Kodi is aborting."""
        if self._monitor.abortRequested():
            return True
        return self._abort_event.is_set()


class CancelToken:
    """Abort flag for one focused item's fetches; fires when superseded or on abort."""

    def __init__(self, service_flag: ServiceAbortFlag):
        self._service = service_flag
        self.max_request_seconds = service_flag.max_request_seconds
        self._cancelled = threading.Event()

    def cancel(self) -> None:
        """Mark this item's in-flight fetches for cancellation (focus moved on)."""
        self._cancelled.set()

    def is_requested(self) -> bool:
        """True if this item was superseded or the service is aborting."""
        return self._cancelled.is_set() or self._service.is_requested()


class OnlineScanMonitor(xbmc.Monitor):
    """Triggers online updater refresh when Kodi finishes a library scan."""

    def __init__(self, online_service: "OnlineServiceMain"):
        super().__init__()
        self._online_service = online_service

    def onNotification(self, sender: str, method: str, data: str) -> None:
        if method == 'VideoLibrary.OnScanFinished':
            self._online_service.request_update()


class OnlineServiceMain(threading.Thread):
    """Coordinator: composes focus/player/music/updater handlers and runs the poll loop."""

    def __init__(self):
        super().__init__(daemon=True)
        self.abort = threading.Event()
        self.abort_flag = ServiceAbortFlag(self.abort)
        # focus/player fetches get the time cap; background work doesn't
        self.capped_abort_flag = ServiceAbortFlag(self.abort, MAX_REQUEST_SECONDS)
        # GIL makes set add/discard/in atomic on CPython, no lock needed
        self.updater_in_progress: set = set()
        self.focus = FocusHandler(self)
        self.player = PlayerHandler(self)
        self.music = MusicPlayerHandler(self)
        self.musicvideo = MusicVideoFocusHandler(self)
        self.updater = UpdaterHandler(self)

    def new_cancel_token(self) -> CancelToken:
        """A fresh per-item cancel token tied to the capped abort flag."""
        return CancelToken(self.capped_abort_flag)

    def request_update(self) -> None:
        """Request the updater to restart its pass (e.g. after library scan)."""
        self.updater.request_restart()

    def run(self) -> None:
        monitor = xbmc.Monitor()
        scan_monitor = OnlineScanMonitor(self)
        log("Service", "Online service started", xbmc.LOGINFO)

        self.updater.start()

        try:
            while not monitor.waitForAbort(ONLINE_POLL_INTERVAL):
                if self.abort.is_set():
                    break
                try:
                    self._loop()
                except Exception as e:
                    log("Service", f"Online service error: {e}", xbmc.LOGWARNING)
        finally:
            del scan_monitor
            log("Service", "Online service stopped", xbmc.LOGINFO)

    def _loop(self) -> None:
        self.focus.process()
        self.player.process()
        self.music.process_audio()
        self.music.process_video()
        self.music.rotate_fanart()
        self.musicvideo.process()
