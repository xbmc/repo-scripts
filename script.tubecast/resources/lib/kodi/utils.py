# -*- coding: utf-8 -*-

import json

from resources.lib.kodi import kodilogging
from resources.lib.tubecast.utils import PY3

import xbmc

import xbmcaddon


import xbmcgui


# read settings
ADDON = xbmcaddon.Addon()
logger = kodilogging.get_logger()


def yes_no(line1, line2=None, line3=None, nolabel=None, yeslabel=None):
    return xbmcgui.Dialog().yesno(heading=ADDON.getAddonInfo('name'),
                                  line1=line1, line2=line2,
                                  nolabel=nolabel,
                                  yeslabel=yeslabel)


def notification(header=ADDON.getAddonInfo('name'), message='', time=5000, icon=ADDON.getAddonInfo('icon'),
                 sound=True):
    xbmcgui.Dialog().notification(header, message, icon, time, sound)


def show_settings():
    ADDON.openSettings()


def get_setting(setting):
    if PY3:
        return ADDON.getSetting(setting).strip()
    return ADDON.getSetting(setting).strip().decode('utf-8')


def set_setting(setting, value):
    ADDON.setSetting(setting, str(value))


def get_device_id():
    return get_infolabel("System.FriendlyName")


def get_setting_as_bool(setting):
    return get_setting(setting).lower() == "true"


def get_setting_as_float(setting):
    try:
        return float(get_setting(setting))
    except ValueError:
        return 0


def get_setting_as_int(setting):
    try:
        return int(get_setting_as_float(setting))
    except ValueError:
        return 0


def get_string(string_id):
    if PY3:
        return ADDON.getLocalizedString(string_id)
    return ADDON.getLocalizedString(string_id).encode('utf-8', 'ignore')


def kodi_json_request(params):
    data = json.dumps(params)
    request = xbmc.executeJSONRPC(data)

    try:
        response = json.loads(request)
    except UnicodeDecodeError:
        response = json.loads(request.decode('utf-8', 'ignore'))

    try:
        if 'result' in response:
            return response['result']
        return None
    except KeyError:
        logger.warn("[%s] %s" %
                    (params['method'], response['error']['message']))
        return None


def get_infolabel(infotag):
    return xbmc.getInfoLabel(infotag)
