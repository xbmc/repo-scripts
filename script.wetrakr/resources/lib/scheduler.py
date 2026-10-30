"""
scheduler.py — decides WHEN the library sync runs, spending as few requests
to WeTrakr as possible. Ticked from the service loop (service_runner.py).

  - Kodi -> WeTrakr is never polled: the monitor and the player know when
    something changed locally. LOCAL_DEBOUNCE after the last change a Local
    pass uploads the diff (zero requests if it is empty).
  - WeTrakr -> Kodi has to be asked (WeTrakr cannot reach the device), so it
    is asked when it matters: shortly after start, after playback stops if the
    last check is older than ACTIVE_STALE, when the device wakes up, and with
    a heartbeat that doubles its interval after every empty check, from
    MIN_INTERVAL up to MAX_INTERVAL. One check is ONE request (/changes
    answers `unchanged`).
  - A Full pass once a day between 3 and 5 in the morning (local time), after
    a library scan that added items (snapshot again) and on "Sync now".
  - Nothing runs while a video is playing: JSON-RPC bursts and dialogs
    stutter playback on many devices.
"""

import random
import threading
import time

import xbmc

from resources.lib import sync_engine
from resources.lib import sync_state as store

STARTUP_DELAY_S = (60, 300)
MIN_INTERVAL_S = 30 * 60
MAX_INTERVAL_S = 6 * 3600
ACTIVE_STALE_S = 10 * 60
LOCAL_DEBOUNCE_S = 5 * 60
FULL_EVERY_S = 20 * 3600
FULL_WINDOW_HOURS = (3, 5)


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log("[WeTrakr] Scheduler: {}".format(msg), level)


class Scheduler(object):

    def __init__(self, monitor, player):
        self.monitor = monitor
        self.player = player
        self.engine = sync_engine.SyncEngine(monitor, player)
        now = time.time()
        self.next_check_at = now + random.randint(*STARTUP_DELAY_S)
        self.interval = MIN_INTERVAL_S
        self.last_check_at = 0
        self.full_minute = random.randint(0, 119)   # minute inside the 3-5 window
        self._thread = None
        self._last_full_at = store.load().get("last_full_at") or 0

    # ─── Signals from the player (see service_runner.py) ───────────

    def playback_stopped(self):
        self.monitor.mark_dirty()
        if time.time() - self.last_check_at > ACTIVE_STALE_S:
            self.next_check_at = min(self.next_check_at, time.time() + 60)

    # ─── Tick ─────────────────────────────────────────────────────

    def tick(self):
        import xbmcaddon
        addon = xbmcaddon.Addon("script.wetrakr")
        if addon.getSetting("sync_enabled") == "false" or not addon.getSetting("api_token") or addon.getSetting("auth_invalid") == "true":
            return
        if self._thread is not None and self._thread.is_alive():
            return
        if self.monitor.reset_requested:
            self.monitor.reset_requested = False
            store.reset()
            self.engine.index.built_at = 0
            self._last_full_at = 0
            self.monitor.full_requested = True
            _log("sync state reset")

        if self.player is not None and self.player.isPlayingVideo():
            return
        now = time.time()

        if self.monitor.full_requested:
            # Dialog only when asked from this Kodi ("Sync now" in the add-on
            # settings); a request from the web runs quietly.
            local = self.monitor.full_requested == "local"
            self.monitor.full_requested = False
            self._start(sync_engine.MODE_FULL, resnapshot=True, with_dialog=local)
            return
        if self.monitor.resnapshot_requested:
            self.monitor.resnapshot_requested = False
            self._start(sync_engine.MODE_FULL, resnapshot=True)
            return
        if self._full_due(now):
            self._start(sync_engine.MODE_FULL, resnapshot=True)
            return
        if self.monitor.dirty_at is not None and now - self.monitor.dirty_at >= LOCAL_DEBOUNCE_S:
            self.monitor.dirty_at = None
            self._start(sync_engine.MODE_LOCAL)
            return
        if self.monitor.check_requested or now >= self.next_check_at:
            self.monitor.check_requested = False
            self._start(sync_engine.MODE_CHECK)

    def _full_due(self, now):
        if now - self._last_full_at < FULL_EVERY_S:
            return False
        lt = time.localtime(now)
        start_h, end_h = FULL_WINDOW_HOURS
        minute_in_window = (lt.tm_hour - start_h) * 60 + lt.tm_min
        return start_h <= lt.tm_hour < end_h and minute_in_window >= self.full_minute

    def _start(self, mode, resnapshot=False, with_dialog=False):
        def _done(result):
            now = time.time()
            self.last_check_at = now
            if mode == sync_engine.MODE_FULL:
                self._last_full_at = now
            if mode != sync_engine.MODE_LOCAL:
                if result.error:
                    self.interval = MIN_INTERVAL_S
                elif result.changed or not result.unchanged:
                    self.interval = MIN_INTERVAL_S
                else:
                    self.interval = min(MAX_INTERVAL_S, self.interval * 2)
                self.next_check_at = now + self.interval
            if result.error and "quota" in result.error.lower():
                self.next_check_at = now + MAX_INTERVAL_S
        _log("starting {} pass".format(mode))
        self._thread = sync_engine.run_in_thread(self.engine, mode, resnapshot=resnapshot, with_dialog=with_dialog, on_done=_done)
