"""Library refresh debouncing and scheduled-interval refresh ticks."""
from __future__ import annotations

import threading
import time
from typing import Optional

import xbmc

from lib.kodi.client import log
from lib.kodi.utilities import set_prop


class RefreshTracker:
    """Owns the library refresh counter (debounced) and scheduled refresh ticks."""

    def __init__(self):
        self._library_refresh_counter = 0
        self._refresh_debounce_timer: Optional[threading.Timer] = None
        self._refresh_timers = {5: 0, 10: 0, 15: 0, 20: 0, 30: 0, 45: 0, 60: 0}
        self._refresh_start_time: Optional[float] = None

    def increment(self) -> None:
        """Bump library refresh counter; debounced 2s before applying to window prop."""
        self._library_refresh_counter += 1
        if self._refresh_debounce_timer is not None:
            self._refresh_debounce_timer.cancel()
        counter = self._library_refresh_counter
        self._refresh_debounce_timer = threading.Timer(2.0, self._apply, args=(counter,))
        self._refresh_debounce_timer.daemon = True
        self._refresh_debounce_timer.start()

    def _apply(self, counter: int) -> None:
        set_prop("SkinInfo.Library.Refreshed", str(counter))
        log("Service", f"Library refreshed (counter: {counter})", xbmc.LOGDEBUG)

    def tick(self) -> None:
        """Bump `SkinInfo.Refresh.{N}min` properties when interval boundaries cross."""
        if self._refresh_start_time is None:
            self._refresh_start_time = time.time()
            for interval in self._refresh_timers:
                set_prop(f"SkinInfo.Refresh.{interval}min", "0")
            return

        elapsed_minutes = int((time.time() - self._refresh_start_time) / 60)
        for interval in self._refresh_timers:
            intervals_passed = elapsed_minutes // interval
            if intervals_passed > self._refresh_timers[interval]:
                self._refresh_timers[interval] = intervals_passed
                set_prop(f"SkinInfo.Refresh.{interval}min", str(intervals_passed))
