#!/usr/bin/python
# -*- coding: utf-8 -*-

from xbmcgui import Dialog

from util.addon_info import ADDON
from util.logging.kodi import translate


def reset():
    """
    Reset all user-set exclusion paths to blanks.
    """
    if Dialog().yesno(translate(32604), translate(32610)):  # Are you sure?
        ADDON.setSettingString(id="exclusion1", value=" ")
        ADDON.setSettingString(id="exclusion2", value=" ")
        ADDON.setSettingString(id="exclusion3", value=" ")
        ADDON.setSettingString(id="exclusion4", value=" ")
        ADDON.setSettingString(id="exclusion5", value=" ")
        Dialog().ok(translate(32630), translate(32631))  # Don't forget to save
