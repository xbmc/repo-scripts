from .common import *
from .store import Store
import xbmc
from .monitor import KodiEventMonitor
from .player import KodiPlayer

def run():
    """
    This is 'main'

    :return:
    """
    footprints()
    # load settings and create the store for our globals
    config = Store()
    Store.kodi_event_monitor = KodiEventMonitor(xbmc.Monitor)
    Store.kodi_player = KodiPlayer(xbmc.Player)

    resumed_playback = Store.kodi_player.resume_if_was_playing()
    if not resumed_playback and not Store.kodi_player.isPlayingVideo():
        Store.kodi_player.autoplay_random_if_enabled()

    while not Store.kodi_event_monitor.abortRequested():
        if Store.kodi_event_monitor.waitForAbort(1):
            # Abort was requested while waiting. We should exit
            break

    footprints(False)



