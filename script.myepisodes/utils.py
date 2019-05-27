# -*- coding: utf-8 -*-

import logging
import xbmc
import xbmcaddon

logger = logging.getLogger(__name__)

_addon = xbmcaddon.Addon()
_icon_path = _addon.getAddonInfo("icon")
_icon = xbmc.translatePath(_icon_path).decode('utf-8')
_scriptname = _addon.getAddonInfo('name')

def getSettingAsBool(setting):
    return _addon.getSetting(setting).lower() == "true"

def getSetting(setting):
    return _addon.getSetting(setting).strip().decode('utf-8', 'replace')

def getSettingAsInt(setting):
    try:
        return int(getSetting(setting))
    except ValueError:
        return 0

def notif(msg, time=5000):
    notif_msg = "%s, %s, %i, %s" % ('MyEpisodes', msg, time, _icon)
    notif_msg = notif_msg.encode('utf-8', 'replace')
    xbmc.executebuiltin("XBMC.Notification(%s)" % notif_msg)

def is_excluded(filename):
    logger.debug("_is_excluded(): Check if '%s' is a URL.", filename)
    excluded_protocols = ["pvr://", "http://", "https://"]
    if any(protocol in filename for protocol in excluded_protocols):
        logger.debug("_is_excluded(): '%s' is a URL; it's excluded.", filename)
        return True

    logger.debug("_is_excluded(): Check if '%s' is in an excluded path.", filename)

    for index in range(1, 4):
        if index == 1:
            index = ''
        exclude_option = getSettingAsBool("ExcludePathOption{}".format(index))
        logger.debug("ExcludePathOption%s", index)
        logger.debug("testing with %s", exclude_option)
        if not exclude_option:
            continue
        exclude_path = getSetting("ExcludePath{}".format(index))
        logger.debug("testing with %s", exclude_path)
        if exclude_path == "":
            continue
        if exclude_path in filename:
            logger.debug("_is_excluded(): Video is excluded (ExcludePath%s).", index)
            return True
    return False
