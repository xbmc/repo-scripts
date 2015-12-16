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


def in_debug_mode():
    return convert_str_to_bool(settings.getSetting("debug"))


def send_debug_reports():
    return convert_str_to_bool(settings.getSetting("debug_reports"))


def chunks(l, n):
    """ Yield successive n-sized chunks from l """
    for i in xrange(0, len(l), n):
        yield l[i:i+n]


def xbmc_print(msg):
    xbmc.log(__name__ + ": " + msg)


def debug(msg):
    """ Prints debug message if debugging is enable in the user settings """
    if in_debug_mode():
        try:
            xbmc_print(str(msg))
        except Exception:
            try:
                xbmc_print("You are trying to print some bad string, " + str(msg).encode("utf-8", "ignore"))
            except Exception:
                xbmc_print("You are trying to print a bad string, I can not even print it")


def notification(header, message, level=0):
    """
    Create a notification and show it in 5 sec
    If debugging is enable in the user settings or the level is 0
    """
    if in_debug_mode() or level == 0:
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


def xbmc_time_to_seconds(timestr):
    seconds = 0
    for part in timestr.split(':'):
        seconds = seconds * 60 + int(part)
    return seconds


def convert_str_to_bool(value):
    if isinstance(value, bool):
        return value
    elif not isinstance(value, str):
        return False
    elif value == 'true':
        return True
    elif value == 'false':
        return False
