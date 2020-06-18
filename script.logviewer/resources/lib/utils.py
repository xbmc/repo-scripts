# -*- coding: utf-8 -*-

import logging
import sys

import xbmc
import xbmcaddon

PY3 = sys.version_info.major >= 3

if PY3:
    def translate(text):
        return ADDON.getLocalizedString(text)

    def encode(s):
        return s.encode("utf-8")

    def decode(s):
        return s.decode("utf-8")

    def str_to_unicode(s):
        return s

else:
    def translate(text):
        return ADDON.getLocalizedString(text).encode("utf-8")

    def encode(s):
        return s

    def decode(s):
        return s

    def str_to_unicode(s):
        return s.decode("utf-8")

ADDON = xbmcaddon.Addon()
ADDON_PATH = str_to_unicode(ADDON.getAddonInfo("path"))
ADDON_NAME = ADDON.getAddonInfo("name")
ADDON_ID = ADDON.getAddonInfo("id")


def get_setting(setting):
    return ADDON.getSetting(setting)


def get_boolean_setting(setting):
    return get_setting(setting) == "true"


def get_int_setting(setting):
    return int(get_setting(setting))


def open_settings():
    ADDON.openSettings()


def get_inverted():
    return get_boolean_setting("invert")


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
    return not get_boolean_setting("custom_window")


def parse_exceptions_only():
    return get_boolean_setting("exceptions_only")


class KodiLogHandler(logging.StreamHandler):
    levels = {
        logging.CRITICAL: xbmc.LOGFATAL,
        logging.ERROR: xbmc.LOGERROR,
        logging.WARNING: xbmc.LOGWARNING,
        logging.INFO: xbmc.LOGINFO,
        logging.DEBUG: xbmc.LOGDEBUG,
        logging.NOTSET: xbmc.LOGNONE,
    }

    def __init__(self):
        super(KodiLogHandler, self).__init__()
        self.setFormatter(logging.Formatter("[{}] %(message)s".format(ADDON_ID)))

    def emit(self, record):
        xbmc.log(self.format(record), self.levels[record.levelno])

    def flush(self):
        pass


def set_logger(name=None, level=logging.DEBUG):
    logger = logging.getLogger(name)
    logger.addHandler(KodiLogHandler())
    logger.setLevel(level)
