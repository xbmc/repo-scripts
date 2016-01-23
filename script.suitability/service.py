# -*- coding: utf-8 -*-
import os
import sys
import xbmc
import xbmcaddon
import xbmcgui

__addon__ = xbmcaddon.Addon(id='script.suitability')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import Settings
from settings import log


###################################
# Main of the Suitability Service
###################################
if __name__ == '__main__':
    log("Suitability: Starting service")

    # Record if the Context menu should be displayed
    if not Settings.showOnContextMenu():
        log("Suitability: Hiding context menu")
        xbmcgui.Window(10025).setProperty("SuitabilityHideContextMenu", "true")
    else:
        log("Suitability: Showing context menu")
        xbmcgui.Window(10025).clearProperty("SuitabilityHideContextMenu")
