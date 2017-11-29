# -*- coding: utf-8 -*-

import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo("path").decode('utf-8')
ADDON_NAME = ADDON.getAddonInfo("name")


def translate(text):
    return ADDON.getLocalizedString(text).encode("utf-8")


def get_setting(setting):
    return ADDON.getSetting(setting)


def open_settings():
    ADDON.openSettings()


def get_inverted():
    return get_setting("invert") == "true"


def get_lines():
    nr_lines = get_setting("lines")
    if nr_lines == "1":
        return 100
    elif nr_lines == "2":
        return 50
    elif nr_lines == "3":
        return 20
    else:
        return 0


def is_default_window():
    return get_setting("custom_window") == "false"
