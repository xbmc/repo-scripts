# -*- coding: utf8 -*-

# Copyright (C) 2016 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmcaddon
import xbmc
import os
import xbmcgui

ADDON = xbmcaddon.Addon()
ID = ADDON.getAddonInfo('id')
ICON = ADDON.getAddonInfo('icon')
NAME = ADDON.getAddonInfo('name')
PATH = ADDON.getAddonInfo('path').decode("utf-8")
MEDIA_PATH = os.path.join(PATH, "resources", "skins", "Default", "media")
VERSION = ADDON.getAddonInfo('version')
DATA_PATH = xbmc.translatePath("special://profile/addon_data/%s" % ID).decode("utf-8")
HOME = xbmcgui.Window(10000)


def setting(setting_name):
    return ADDON.getSetting(setting_name)


def set_setting(setting_name, string):
    ADDON.setSetting(setting_name, string)


def bool_setting(setting_name):
    return ADDON.getSetting(setting_name) == "true"


def reload_addon():
    global ADDON
    ADDON = xbmcaddon.Addon()


def LANG(label_id):
    if 31000 <= label_id <= 33000:
        return ADDON.getLocalizedString(label_id)
    else:
        return xbmc.getLocalizedString(label_id)


def set_global(setting_name, setting_value):
    HOME.setProperty(setting_name, setting_value)


def get_global(setting_name):
    HOME.getProperty(setting_name)


def clear_global(setting_name):
    HOME.clearProperty(setting_name)


def clear_globals():
    HOME.clearProperties()
