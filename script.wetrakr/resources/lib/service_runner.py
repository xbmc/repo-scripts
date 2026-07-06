"""
service_runner.py — main loop of the WeTrakr Scrobbler background service.

Handles the device-code authentication on first launch and then runs the
periodic playback progress checks until Kodi requests an abort.
"""

import xbmc
import xbmcaddon

from resources.lib import auth
from resources.lib.player import WeTrakrPlayer
from resources.lib.notification import notify as _notify

POLL_INTERVAL = 30  # seconds between progress checks


def run():
    addon = xbmcaddon.Addon("script.wetrakr")
    xbmc.log(
        "[WeTrakr] Service started (v{})".format(addon.getAddonInfo("version")),
        xbmc.LOGINFO
    )

    if not auth.is_authenticated():
        xbmc.log("[WeTrakr] Not authenticated — starting device code flow", xbmc.LOGINFO)
        if not auth.run_device_auth_flow():
            xbmc.log(
                "[WeTrakr] Auth flow cancelled or failed — service will wait for manual setup",
                xbmc.LOGINFO
            )

    monitor = xbmc.Monitor()
    player = WeTrakrPlayer()
    warned_reauth = False

    while not monitor.abortRequested():
        # If a scrobble was rejected with 401/403, the saved token is stale and
        # the user must reconnect. Never open the auth dialog while a video is
        # playing — a WindowDialog mid-playback renegotiates the renderer and can
        # freeze passthrough audio. Warn once (non-blocking) and re-login only
        # once playback has stopped.
        if auth.token_was_rejected():
            if not warned_reauth:
                _notify("WeTrakr", "Connection expired — please reconnect", 8000)
                warned_reauth = True
            if not player.isPlayingVideo():
                xbmc.log("[WeTrakr] Stale token — re-running device code flow", xbmc.LOGINFO)
                auth.run_device_auth_flow()
                warned_reauth = False
        else:
            warned_reauth = False
            if player.isPlayingVideo() and player.current_item and not player.scrobbled:
                player.check_progress()

        if monitor.waitForAbort(POLL_INTERVAL):
            break

    xbmc.log("[WeTrakr] Service stopped", xbmc.LOGINFO)
