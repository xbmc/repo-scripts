"""
Helper Functions
"""

import xbmc
import xbmcaddon
import xbmcgui

__name__ = "EpisodeHunter"


def debug(msg):
    """ Prints debug message if debugging is enable in the user settings """
    settings = xbmcaddon.Addon("script.episodehunter")
    is_debuging = settings.getSetting("debug")
    if is_debuging:
        try:
            xbmc.log(__name__ + ": " + msg)
        except Exception:
            try:
                xbmc.log(__name__ + ": You are trying to print some bad string, " + msg.encode("utf-8", "ignore"))
            except Exception:
                xbmc.log(__name__ + ": You are trying to print a bad string, I can not even print it")


def notification(header, message, level=0):
    """
    Create a notification and show it in 5 sec
    If debugging is enable in the user settings or the level is 0
    """
    settings = xbmcaddon.Addon("script.episodehunter")
    is_debuging = settings.getSetting("debug")
    if is_debuging or level == 0:
        xbmc.executebuiltin("XBMC.Notification(%s,%s,%i,%s)" % (header, message, 5000, settings.getAddonInfo("icon")))


def is_settings_okey(daemon=False, silent=False):
    """ Check if we have username and api key? """
    settings = xbmcaddon.Addon("script.episodehunter")
    language = settings.getLocalizedString

    if settings.getSetting("username") == "" and settings.getSetting("api_key") == "":
        if silent:
            return False
        elif daemon:
            notification(__name__, language(32014))
        else:
            xbmcgui.Dialog().ok(__name__, language(32014))
        return False

    elif settings.getSetting("username") == "":
        if silent:
            return False
        if daemon:
            notification(__name__, language(32012))
        else:
            xbmcgui.Dialog().ok(__name__, language(32012))
        return False

    elif settings.getSetting("api_key") == "":
        if silent:
            return False
        if daemon:
            notification(__name__, language(32013))
        else:
            xbmcgui.Dialog().ok(__name__, language(32013))
        return False

    return True


def not_seen_movie(imdb, array):
    for x in array:
        if imdb == x['imdb_id']:
            return False
    return True


def seen_episode(e, array):
    for i in range(0, len(array)):
        if e == array[i]:
            return True
    return False


def is_not_in(test, array):
    for x in array:
        if test in x:
            return False
    return True


def to_seconds(timestr):
    seconds = 0
    for part in timestr.split(':'):
        seconds = seconds * 60 + int(part)
    return seconds
