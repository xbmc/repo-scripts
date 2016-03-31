#!/usr/bin/python
# -*- coding: utf-8 -*-

import xbmcaddon
import xbmcgui
import utils

# Addon info
__addonID__ = "script.filecleaner"
__addon__ = xbmcaddon.Addon(__addonID__)


def reset_exclusions():
    """
    Reset all user-set exclusion paths to blanks.
    :return:
    """
    if xbmcgui.Dialog().yesno(utils.translate(32604), utils.translate(32610), utils.translate(32607)):
        __addon__.setSetting(id="exclusion1", value="")
        __addon__.setSetting(id="exclusion2", value="")
        __addon__.setSetting(id="exclusion3", value="")

reset_exclusions()
