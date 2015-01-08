import xbmcaddon

from resources.lib import helper

settings = xbmcaddon.Addon('script.episodehunter')


def username():
    return settings.getSetting('username')


def api_key():
    return settings.getSetting('api_key')


def offline():
    return helper.convert_str_to_bool(settings.getSetting('offline'))


def scrobble_movies():
    return helper.convert_str_to_bool(settings.getSetting('scrobble_movie'))


def scrobble_episodes():
    return helper.convert_str_to_bool(settings.getSetting('scrobble_episode'))


def scrobble_min_view_time():
    return settings.getSetting("scrobble_min_view_time")
