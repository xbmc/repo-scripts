import xbmc
# noinspection PyPackages
from .monitor import KodiEventMonitor
# noinspection PyPackages
from .player import KodiPlayer
# noinspection PyPackages
from .store import Store

from bossanova808.logger import Logger


def run():
    """
    Start the addon: initialize logging and global state, configure Kodi monitor and player, attempt to resume or start playback, then run the main event loop until an abort is requested.
    
    This function:
    - Starts the logger and creates the global Store.
    - Instantiates and stores Kodi event monitor and player objects.
    - Attempts to resume previous playback; if nothing resumed and no video is playing, triggers autoplay when enabled.
    - Enters a loop that waits for an abort request and exits when one is detected.
    - Stops the logger before returning.
    """
    Logger.start()
    # load settings and create the store for our globals
    Store()
    Store.kodi_event_monitor = KodiEventMonitor(xbmc.Monitor)
    Store.kodi_player = KodiPlayer(xbmc.Player)

    resumed_playback = Store.kodi_player.resume_if_was_playing()
    if not resumed_playback and not Store.kodi_player.isPlayingVideo():
        Store.kodi_player.autoplay_random_if_enabled()

    while not Store.kodi_event_monitor.abortRequested():
        if Store.kodi_event_monitor.waitForAbort(1):
            Logger.debug('onAbortRequested')
            # Abort was requested while waiting. We should exit
            break

    Logger.stop()
