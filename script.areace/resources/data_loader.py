import xbmcaddon
from resources.telegram import fetch

ADDON = xbmcaddon.Addon()

def load_telegram(settings):
    enabled = settings.getBool('telegram.isEnabled')
    if (not enabled): return []
    opts = {
        'token': settings.getString('telegram.token'), 
        'offset': settings.getInt('telegram.offset')
    }
    return fetch(opts)


def load_data():
    settings = ADDON.getSettings()
    return load_telegram(settings)