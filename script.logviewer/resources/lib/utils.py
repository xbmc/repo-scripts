# -*- coding: utf-8 -*-

import sys

import xbmcaddon

PY3 = sys.version_info.major >= 3

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo("path")
ADDON_NAME = ADDON.getAddonInfo("name")

if PY3:
    def translate(text):
        return ADDON.getLocalizedString(text)
else:
    ADDON_PATH = ADDON_PATH.decode("utf-8")

    def translate(text):
        return ADDON.getLocalizedString(text).encode("utf-8")


def get_setting(setting):
    return ADDON.getSetting(setting)


def get_boolean(setting):
    return get_setting(setting) == "true"


def open_settings():
    ADDON.openSettings()


def get_inverted():
    return get_boolean("invert")


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
    return not get_boolean("custom_window")


def parse_exceptions_only():
    return get_boolean("exceptions_only")
