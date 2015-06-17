"""
Helper Functions
"""

import xbmc
import xbmcaddon
import xbmcgui

from resources.exceptions import SettingsExceptions

__name__ = "EpisodeHunter"
settings = xbmcaddon.Addon("script.episodehunter")
language = settings.getLocalizedString


def get_addon_resource_path(path):
    return xbmc.translatePath(settings.getAddonInfo('profile') + path)


def get_username():
    return settings.getSetting("username")


def get_api_key():
    return settings.getSetting("api_key")


def chunks(l, n):
    """ Yield successive n-sized chunks from l """
    for i in xrange(0, len(l), n):
        yield l[i:i+n]


def xbmc_print(msg):
    xbmc.log(__name__ + ": " + msg)


def debug(msg):
    """ Prints debug message if debugging is enable in the user settings """
    is_debuging = settings.getSetting("debug")
    if is_debuging:
        try:
            xbmc_print(str(msg))
        except Exception:
            try:
                xbmc_print("You are trying to print some bad string, " + str(msg).encode("utf-8", "ignore"))
            except Exception:
                xbmc_print("You are trying to print a bad string, I can not even print it")


def print_exception_information():
    import traceback
    stack_trace = traceback.format_exc()
    debug(stack_trace)


def notification(header, message, level=0):
    """
    Create a notification and show it in 5 sec
    If debugging is enable in the user settings or the level is 0
    """
    is_debuging = settings.getSetting("debug")
    if is_debuging or level == 0:
        xbmc.executebuiltin("XBMC.Notification(%s,%s,%i,%s)" % (header, message, 5000, settings.getAddonInfo("icon")))


def check_user_credentials():
    """
    Make a local check of the user credentials
    May raise SettingsExceptions
    :rtype : bool
    """
    if get_username() == "" and get_api_key() == "":
        raise SettingsExceptions(language(32014))
    elif settings.getSetting("username") == "":
        raise SettingsExceptions(language(32012))
    elif settings.getSetting("api_key") == "":
        raise SettingsExceptions(language(32013))
    return True


def is_settings_okey(daemon=False, silent=False):
    """ Check if we have username and api key? """
    try:
        return check_user_credentials()
    except SettingsExceptions:
        if silent:
            return False
        elif daemon:
            notification(__name__, language(32014))
        else:
            xbmcgui.Dialog().ok(__name__, language(32014))
        return False


def not_seen_movie(imdb, array):
    for x in array:
        if imdb == x['imdb_id']:
            return False
    return True

def seen_movie(imdb, array_of_movies):
    for movie in array_of_movies:
        if imdb == movie['imdb_id']:
            return True
    return False


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


def xbmc_time_to_seconds(timestr):
    seconds = 0
    for part in timestr.split(':'):
        seconds = seconds * 60 + int(part)
    return seconds


def convert_str_to_bool(value):
    if isinstance(value, bool):
        return value
    elif not isinstance(value, str):
        return None
    elif value == 'true':
        return True
    elif value == 'false':
        return False
