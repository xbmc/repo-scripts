import xbmc
import xbmcaddon
from resources.config import __NAME__

settings = xbmcaddon.Addon("script.episodehunter")


def username():
    return settings.getSetting('username')


def api_key():
    return settings.getSetting('api_key')


def scrobble_movies():
    return convert_str_to_bool(settings.getSetting('scrobble_movie'))


def scrobble_episodes():
    return convert_str_to_bool(settings.getSetting('scrobble_episode'))


def scrobble_min_view_time():
    return settings.getSetting("scrobble_min_view_time")


def in_debug_mode():
    return convert_str_to_bool(settings.getSetting("debug"))


def xbmc_print(msg):
    xbmc.log(__NAME__ + ": " + msg)


def debug(msg):
    if in_debug_mode():
        try:
            xbmc_print(str(msg))
        except Exception:
            try:
                xbmc_print("You are trying to print some bad string, " +
                           str(msg).encode("utf-8", "ignore"))
            except Exception:
                xbmc_print(
                    "You are trying to print a bad string, I can not even print it")


def valid_user_credentials():
    if username() == "" or api_key() == "":
        return False
    else:
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
        return False
    elif value == 'true':
        return True
    elif value == 'false':
        return False
