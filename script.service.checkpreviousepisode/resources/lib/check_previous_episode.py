from bossanova808.constants import TRANSLATE
from bossanova808.logger import Logger
# noinspection PyPackages
from .store import Store
# noinspection PyPackages
from .monitor import KodiEventMonitor
# noinspection PyPackages
from .player import KodiPlayer


def manage_ignored():
    """
    Manage ignored shows in settings...

    :return:
    """

    Logger.info("Managing ignored shows...")
    Store.get_ignored_shows_from_config_file()
    Store.ignored_shows.manage(TRANSLATE(32062), TRANSLATE(32060))


def run(args):
    """
    This is 'main'

    :return:
    """
    try:
        Logger.start()
        # Initialise the global store and load the addon settings
        Store()

        # TWO RUN-MODES - we're either running as a service, or we're running the tool to manage ignored shows...

        # MANAGE IGNORED SHOWS
        if len(args) > 1 and args[1].startswith('ManageIgnored'):
            manage_ignored()
        # DEFAULT - RUN AS A SERVICE & WATCH PLAYBACK EVENTS
        else:
            Logger.info("Listening to onAVStarted for episode playback.")
            kodi_event_monitor = KodiEventMonitor()
            # Keep instance alive to receive Kodi player events
            _kodi_player = KodiPlayer()

            while not kodi_event_monitor.waitForAbort(1):
                pass
            Logger.debug('Abort Requested')

    finally:
        Logger.stop()
