"""
service.py — xbmc.Monitor subclass; the long-running service loop.

Responsibilities:
  • Instantiate Cache, APIClient, and PunchPlayPlayer.
  • Block with waitForAbort() so Kodi can signal a clean shutdown.
  • Periodically flush the offline scrobble queue (every 60 s when online).
  • Prune stale identifier-cache entries once per day.
  • Reload settings when the user changes them via onSettingsChanged().
"""

import time

import xbmc
import xbmcaddon
import xbmcgui

_ADDON_ID = "script.punchplay"

# Flush the offline queue this often when network is available (seconds).
_FLUSH_INTERVAL = 60

# Prune the identifier cache this often (seconds).  24 h.
_PRUNE_INTERVAL = 86_400


class PunchPlayService(xbmc.Monitor):
    def __init__(self) -> None:
        super().__init__()

        from cache import Cache
        from api import APIClient
        from player import PunchPlayPlayer

        self._cache = Cache()
        self._api = APIClient(cache=self._cache)
        self._player = PunchPlayPlayer(api=self._api, cache=self._cache)

        self._last_flush = 0.0
        self._last_prune = 0.0

    # ------------------------------------------------------------------
    # Monitor callbacks
    # ------------------------------------------------------------------

    def onSettingsChanged(self) -> None:  # type: ignore[override]
        xbmc.log("[PunchPlay] Settings changed — will apply on next event", xbmc.LOGDEBUG)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        addon = xbmcaddon.Addon(_ADDON_ID)
        xbmc.log(
            f"[PunchPlay] Service started (v{addon.getAddonInfo('version')})",
            xbmc.LOGINFO,
        )

        # Window 10000 is the Kodi home window — its properties are globally
        # accessible, so settings action buttons can signal the service here.
        _home = xbmcgui.Window(10000)

        while not self.abortRequested():
            now = time.monotonic()

            # Handle login / logout triggered from the settings screen.
            if _home.getProperty("punchplay_login"):
                _home.clearProperty("punchplay_login")
                xbmc.log("[PunchPlay] Login triggered from settings", xbmc.LOGINFO)
                self._api.device_code_login()

            if _home.getProperty("punchplay_logout"):
                _home.clearProperty("punchplay_logout")
                xbmc.log("[PunchPlay] Logout triggered from settings", xbmc.LOGINFO)
                self._api.logout()

            # Flush offline queue periodically.
            if self._api.is_authenticated() and (now - self._last_flush >= _FLUSH_INTERVAL):
                try:
                    self._api.flush_queue()
                except Exception as exc:
                    xbmc.log(f"[PunchPlay] Queue flush error: {exc}", xbmc.LOGDEBUG)
                self._last_flush = now

            # Prune stale identifier cache entries once a day.
            if now - self._last_prune >= _PRUNE_INTERVAL:
                try:
                    self._cache.prune_identifier_cache()
                    xbmc.log("[PunchPlay] Identifier cache pruned", xbmc.LOGDEBUG)
                except Exception as exc:
                    xbmc.log(f"[PunchPlay] Cache prune error: {exc}", xbmc.LOGDEBUG)
                self._last_prune = now

            # Sleep 1 s so login/logout feel responsive.
            self.waitForAbort(1)

        # Kodi is shutting down — clean up the player.
        self._player.cleanup()
        xbmc.log("[PunchPlay] Service stopped", xbmc.LOGINFO)
