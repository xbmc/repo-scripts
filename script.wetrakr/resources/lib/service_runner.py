"""
service_runner.py — main loop of the WeTrakr Scrobbler background service.

Handles the device-code authentication (at start once WeTrakr is reachable,
and again with backoff while not connected), then runs the
periodic playback progress checks and the library sync scheduler until Kodi
requests an abort.
"""

import time

import xbmc
import xbmcaddon

from resources.lib import auth
from resources.lib.player import WeTrakrPlayer
from resources.lib.notification import notify as _notify
from resources.lib.sync_monitor import SyncMonitor
from resources.lib.scheduler import Scheduler

POLL_INTERVAL = 30  # seconds between progress checks


# Waits between automatic login attempts while WeTrakr can't be reached or
# the QR code expired unanswered (seconds); the last one repeats.
AUTH_RETRY = [60, 120, 300, 900, 1800]
BOOT_NETWORK_WAIT = 120  # seconds to wait for the network after Kodi starts


class _AuthRetry(object):
    """When the service may open the login dialog on its own.

    Before 1.3.3 a failed login was never retried at start, and a rejected
    token re-ran the flow every POLL_INTERVAL seconds, with a "Could not
    connect" dialog each time the server could not be reached.
    """

    def __init__(self):
        self.next_at = 0.0
        self.failures = 0
        self.expired = 0
        self.paused = False     # closed by the user, or ignored twice

    def due(self):
        return not self.paused and time.time() >= self.next_at

    def record(self, outcome):
        if outcome == auth.AUTH_OK:
            self.__init__()
        elif outcome == auth.AUTH_CANCELLED:
            self.paused = True
            _notify("WeTrakr", "Not connected. Use Connect in the add-on settings.", 6000)
        elif outcome == auth.AUTH_EXPIRED and self.expired >= 1:
            # Twice on screen and nobody answered: stop popping it up.
            self.paused = True
            _notify("WeTrakr", "Not connected. Use Connect in the add-on settings.", 6000)
        elif outcome in (auth.AUTH_OFFLINE, auth.AUTH_EXPIRED):
            if outcome == auth.AUTH_EXPIRED:
                self.expired += 1
            wait = AUTH_RETRY[min(self.failures, len(AUTH_RETRY) - 1)]
            self.failures += 1
            self.next_at = time.time() + wait
            xbmc.log("[WeTrakr] Login {}: next try in {} s".format(outcome, wait), xbmc.LOGINFO)
        # AUTH_BUSY: Connect from the settings is on screen right now.


def run():
    addon = xbmcaddon.Addon("script.wetrakr")
    xbmc.log(
        "[WeTrakr] Service started (v{})".format(addon.getAddonInfo("version")),
        xbmc.LOGINFO
    )

    player = WeTrakrPlayer()
    # The monitor listens to library events (manual marks, scans, wake) and
    # the scheduler decides when the library sync runs. The player tells them
    # what is playing so its own plays are not uploaded twice.
    monitor = SyncMonitor(player)
    scheduler = Scheduler(monitor, player)
    player.sync_monitor = monitor
    player.scheduler = scheduler
    retry = _AuthRetry()
    warned_reauth = False

    if not auth.is_authenticated():
        # Right after boot the network is often not up yet: wait for it
        # quietly instead of failing the first login with a dialog.
        xbmc.log("[WeTrakr] Not authenticated: waiting for WeTrakr to be reachable", xbmc.LOGINFO)
        if auth.wait_for_server(monitor, BOOT_NETWORK_WAIT):
            retry.record(auth.run_device_auth_flow(interactive=False))
        else:
            retry.record(auth.AUTH_OFFLINE)

    while not monitor.abortRequested():
        # Never open the auth dialog while a video is playing: a WindowDialog
        # mid-playback renegotiates the renderer and can freeze passthrough
        # audio. A rejected token (401/403 on a scrobble or a sync) gets one
        # non-blocking warning and the re-login waits until playback stops.
        if not auth.is_authenticated():
            if auth.token_was_rejected() and not warned_reauth:
                _notify("WeTrakr", "Connection expired, please reconnect", 8000)
                warned_reauth = True
            if retry.due() and not player.isPlayingVideo():
                if auth.server_reachable():
                    xbmc.log("[WeTrakr] Not authenticated: starting device code flow", xbmc.LOGINFO)
                    retry.record(auth.run_device_auth_flow(interactive=False))
                else:
                    retry.record(auth.AUTH_OFFLINE)
        else:
            warned_reauth = False
            if retry.paused or retry.failures:
                retry.record(auth.AUTH_OK)     # connected from the settings
            if player.isPlayingVideo() and player.current_item and not player.scrobbled:
                player.check_progress()
            try:
                scheduler.tick()
            except Exception as e:
                xbmc.log("[WeTrakr] Scheduler tick error: {}".format(e), xbmc.LOGERROR)

        if monitor.waitForAbort(POLL_INTERVAL):
            break

    xbmc.log("[WeTrakr] Service stopped", xbmc.LOGINFO)
