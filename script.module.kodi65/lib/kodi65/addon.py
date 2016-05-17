# -*- coding: utf8 -*-

# Copyright (C) 2016 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmcaddon
import xbmc
import os
import xbmcgui

ADDON = xbmcaddon.Addon()
ID = ADDON.getAddonInfo('id').decode("utf-8")
ICON = ADDON.getAddonInfo('icon').decode("utf-8")
NAME = ADDON.getAddonInfo('name').decode("utf-8")
FANART = ADDON.getAddonInfo('fanart').decode("utf-8")
AUTHOR = ADDON.getAddonInfo('author').decode("utf-8")
CHANGELOG = ADDON.getAddonInfo('changelog').decode("utf-8")
DESCRIPTION = ADDON.getAddonInfo('description').decode("utf-8")
DISCLAIMER = ADDON.getAddonInfo('disclaimer').decode("utf-8")
VERSION = ADDON.getAddonInfo('version').decode("utf-8")
PATH = ADDON.getAddonInfo('path').decode("utf-8")
PROFILE = ADDON.getAddonInfo('profile').decode("utf-8")
SUMMARY = ADDON.getAddonInfo('summary').decode("utf-8")
TYPE = ADDON.getAddonInfo('type').decode("utf-8")
MEDIA_PATH = os.path.join(PATH, "resources", "skins", "Default", "media")
DATA_PATH = xbmc.translatePath("special://profile/addon_data/%s" % ID).decode("utf-8")
HOME = xbmcgui.Window(10000)


def setting(setting_name):
    return ADDON.getSetting(setting_name)


def set_setting(setting_name, string):
    ADDON.setSetting(str(setting_name), str(string))


def bool_setting(setting_name):
    return ADDON.getSetting(setting_name) == "true"


def reload_addon():
    global ADDON
    ADDON = xbmcaddon.Addon()


def LANG(id_):
    return ADDON.getLocalizedString(id_) if 31000 <= id_ <= 33000 else xbmc.getLocalizedString(id_)


def set_global(setting_name, setting_value):
    HOME.setProperty(setting_name, setting_value)


def get_global(setting_name):
    return HOME.getProperty(setting_name)


def clear_global(setting_name):
    HOME.clearProperty(setting_name)


def clear_globals():
    HOME.clearProperties()
