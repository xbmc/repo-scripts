"""
service_runner.py — main loop of the WeTrakr Scrobbler background service.

Handles the device-code authentication on first launch and then runs the
periodic playback progress checks until Kodi requests an abort.
"""

import xbmc
import xbmcaddon

from resources.lib import auth
from resources.lib.player import WeTrakrPlayer

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

    while not monitor.abortRequested():
        if player.isPlayingVideo() and player.current_item and not player.scrobbled:
            player.check_progress()

        if monitor.waitForAbort(POLL_INTERVAL):
            break

    xbmc.log("[WeTrakr] Service stopped", xbmc.LOGINFO)
