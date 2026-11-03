"""Online data service: coordinator thread composing focus/player/music/updater handlers."""
from __future__ import annotations

import threading
from typing import Final

import xbmc

from lib.kodi.client import log
from lib.infrastructure.tasks import ServiceAbortFlag
from lib.kodi.utilities import LabelSnapshot
from lib.service.online.focus import FOCUS_LABELS, FocusHandler
from lib.service.online.player import PlayerHandler
from lib.service.online.musicplayer import MusicPlayerHandler
from lib.service.online.musicvideo import FOCUS_LABELS as MUSICVIDEO_LABELS
from lib.service.online.musicvideo import MusicVideoFocusHandler
from lib.service.online.pvr import FOCUS_LABELS as PVR_LABELS
from lib.service.online.pvr import PvrFocusHandler, PvrPlayerHandler
from lib.data.pvr import MATCH_CHANGED
from lib.service.online.updater import UpdaterHandler


ONLINE_POLL_INTERVAL: Final = 0.10

MAX_REQUEST_SECONDS: Final = 30.0  # runaway backstop; shutdown handled by the connection watcher


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
    """Monitor asking for an updater refresh on a library scan and a PVR reread on a new match."""

    def __init__(self, online_service: "OnlineServiceMain"):
        super().__init__()
        self._online_service = online_service

    def onNotification(self, sender: str, method: str, data: str) -> None:
        """Ask for an update once a library scan finishes; reread the programme on a new match."""
        if method == 'VideoLibrary.OnScanFinished':
            self._online_service.request_update()
        elif method == f'Other.{MATCH_CHANGED}':
            self._online_service.pvr.forget()
            self._online_service.pvr_player.forget()


class OnlineServiceMain(threading.Thread):
    """Coordinator: composes focus/player/music/updater handlers and runs the poll loop."""

    def __init__(self):
        super().__init__(daemon=True)
        self.abort = threading.Event()
        self.abort_flag = ServiceAbortFlag(self.abort)
        # focus/player fetches get the time cap; background work doesn't
        self.capped_abort_flag = ServiceAbortFlag(self.abort, MAX_REQUEST_SECONDS)
        # set add, discard and membership are atomic under the GIL
        self.updater_in_progress: set = set()
        self.focus = FocusHandler(self)
        self.player = PlayerHandler(self)
        self.music = MusicPlayerHandler(self)
        self.musicvideo = MusicVideoFocusHandler(self)
        self.pvr = PvrFocusHandler(self)
        self.pvr_player = PvrPlayerHandler(self)
        self.updater = UpdaterHandler(self)

    def new_cancel_token(self) -> CancelToken:
        """A fresh per-item cancel token tied to the capped abort flag."""
        return CancelToken(self.capped_abort_flag)

    def request_update(self) -> None:
        """Request the updater to restart its pass (e.g. after library scan)."""
        self.updater.request_restart()

    def run(self) -> None:
        """Run the online service poll loop until Kodi aborts."""
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
        """One pass over the focus, player, music, musicvideo and both PVR handlers."""
        labels = LabelSnapshot((*FOCUS_LABELS, *MUSICVIDEO_LABELS, *PVR_LABELS))
        self.focus.process(labels)
        self.player.process()
        self.music.process()
        self.music.rotate_fanart()
        self.musicvideo.process(labels)
        self.pvr.process(labels)
        self.pvr_player.process(labels)
