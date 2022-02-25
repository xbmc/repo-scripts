from .common import *
from .store import Store
from .monitor import KodiEventMonitor
from .player import KodiPlayer
import xbmc
import os


def manage_ignored():
    """
    Manage ignored shows in settings..

    :return:
    """

    log("Managing ignored shows...")
    dialog = xbmcgui.Dialog()
    Store.get_ignored_shows_from_config_file()

    # Short circuit if no ignored shows, so nothing to manage...
    if len(Store.ignored_shows) < 1:
        notify(LANGUAGE(32060), xbmcgui.NOTIFICATION_INFO, 5000)
        return

    # Ok, there are ignored shows in the list...

    # Convert our dict to a list for the dialog...
    ignored_list = []
    for key, value in list(Store.ignored_shows.items()):
        ignored_list.append(value)

    if ignored_list:
        selected = dialog.select(LANGUAGE(32062), ignored_list)
        if selected != -1:
            show_title = ignored_list[selected]
            log("User has requested we stop ignoring: " + show_title)
            log("Ignored shows before removal is: " + str(Store.ignored_shows))
            # find the key (tv_show_id) for this show& remove from dict
            key = list(Store.ignored_shows.keys())[list(Store.ignored_shows.values()).index(show_title)]
            Store.ignored_shows.pop(key, None)
            log("Ignored shows  after removal is: " + str(Store.ignored_shows))

            # No ignored shows?  Clean up & delete the empty file..
            if len(Store.ignored_shows) == 0:
                if os.path.exists(Store.ignored_shows_file):
                    os.remove(Store.ignored_shows_file)
            else:
                # write the ignored list back out
                Store.write_ignored_shows_to_config(Store.ignored_shows)


def run(args):
    """
    This is 'main'

    :return:
    """
    footprints()
    # Initialise the global store and load the addon settings
    config = Store()

    # TWO RUN-MODES - we're either running as a service, or we're running the tool to manage ignored shows..

    # MANAGE IGNORED SHOWS
    if len(args) > 1:
        try:
            if args[1].startswith('ManageIgnored'):
                manage_ignored()
        # if not, carry on, nothing to see here...
        except Exception as inst:
            log("Exception in manage_ignored " + format_exc(inst))

    # DEFAULT - RUN AS A SERVICE & WATCH PLAYBACK EVENTS
    else:
        log("Listening to onAvStarted for episode playback.")
        Store.kodi_event_monitor = KodiEventMonitor(xbmc.Monitor)
        Store.kodi_player = KodiPlayer(xbmc.Player)

        while not Store.kodi_event_monitor.abortRequested():
            # Sleep/wait for abort for 10 seconds
            if Store.kodi_event_monitor.waitForAbort(1):
                # Abort was requested while waiting. We should exit
                break

    footprints(False)
















