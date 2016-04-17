# -*- coding: utf-8 -*-
import xbmcgui

# Import the common settings
from resources.lib.settings import Settings
from resources.lib.settings import log


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
