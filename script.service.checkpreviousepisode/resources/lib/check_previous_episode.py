import xbmcgui

from bossanova808.constants import TRANSLATE
from bossanova808.logger import Logger
from bossanova808.notify import Notify
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
    dialog = xbmcgui.Dialog()
    Store.get_ignored_shows_from_config_file()

    # Short circuit if no ignored shows, so nothing to manage...
    if len(Store.ignored_shows) < 1:
        Notify.info(TRANSLATE(32060), 5000)
        return

    # OK, there are ignored shows in the list...

    # Build a sorted (id, title) list for stable mapping and to handle duplicate titles
    sorted_pairs = sorted(
            Store.ignored_shows.items(),
            key=lambda kv:((kv[1] or '').casefold(), str(kv[0]))
    )
    labels = [title for (_, title) in sorted_pairs]

    if labels:
        selected = dialog.select(TRANSLATE(32062), labels)
        if selected != -1:
            tvshow_id, show_title = sorted_pairs[selected]
            Logger.info("User has requested we stop ignoring: " + show_title)
            Logger.debug("Ignored shows before removal is: " + str(Store.ignored_shows))
            Store.ignored_shows.pop(tvshow_id, None)
            Logger.debug("Ignored shows after removal is: " + str(Store.ignored_shows))
            Store.write_ignored_shows_to_config()


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
