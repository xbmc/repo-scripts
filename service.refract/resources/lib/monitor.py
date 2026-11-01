"""The background loop: runs while Kodi runs and marks finished plays on Refract."""
import xbmc

from resources.lib import kodi
from resources.lib.player import RefractPlayer


def run():
    monitor = xbmc.Monitor()
    player = RefractPlayer()
    kodi.log("started")
    while not monitor.abortRequested():
        player.tick()
        if monitor.waitForAbort(5):
            break
    kodi.log("stopped")

