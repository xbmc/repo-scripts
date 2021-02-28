# -*- coding: utf-8 -*-

import logging
import xbmc
import xbmcvfs
import xbmcaddon

logger = logging.getLogger(__name__)

_addon = xbmcaddon.Addon()
_icon_path = _addon.getAddonInfo("icon")
_icon = xbmcvfs.translatePath(_icon_path)
_scriptname = _addon.getAddonInfo("name")


def getSettingAsBool(setting):
    return _addon.getSetting(setting).lower() == "true"


def getSetting(setting):
    return _addon.getSetting(setting).strip()


def getSettingAsInt(setting):
    try:
        return int(getSetting(setting))
    except ValueError:
        return 0


def notif(msg, time=5000):
    xbmc.executebuiltin(f"Notification(MyEpisodes, {msg}, {time}, {_icon})")


def is_excluded(filename):
    logger.debug(f"_is_excluded(): Check if '{filename}' is a URL.")
    excluded_protocols = ["pvr://", "http://", "https://"]
    if any(protocol in filename for protocol in excluded_protocols):
        logger.debug(f"_is_excluded(): '{filename}' is a URL; it's excluded.")
        return True

    logger.debug(f"_is_excluded(): Check if '{filename}' is in an excluded path.")

    for index in range(1, 4):
        if index == 1:
            index = ""
        exclude_option = getSettingAsBool(f"ExcludePathOption{index}")
        logger.debug(f"ExcludePathOption{index}")
        logger.debug(f"testing with {exclude_option}")
        if not exclude_option:
            continue
        exclude_path = getSetting(f"ExcludePath{index}")
        logger.debug(f"testing with {exclude_path}")
        if exclude_path == "":
            continue
        if exclude_path in filename:
            logger.debug(f"_is_excluded(): Video is excluded (ExcludePath{index}).")
            return True
    return False
