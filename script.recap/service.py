# -*- coding: utf-8 -*-
import xbmcgui

# Import the common settings
from resources.lib.settings import Settings
from resources.lib.settings import log


###################################
# Main of the Recap Service
###################################
if __name__ == '__main__':
    log("Recap: Starting service")

    # Record if the Context menu should be displayed
    if not Settings.showOnContextMenu():
        log("Recap: Hiding context menu")
        xbmcgui.Window(10025).setProperty("RecapHideContextMenu", "true")
    else:
        log("Recap: Showing context menu")
        xbmcgui.Window(10025).clearProperty("RecapHideContextMenu")

    if not Settings.showPreviousOnContextMenu():
        log("Recap: Hiding Previous context menu")
        xbmcgui.Window(10025).setProperty("RecapPreviousHideContextMenu", "true")
    else:
        log("Recap: Showing Previous context menu")
        xbmcgui.Window(10025).clearProperty("RecapPreviousHideContextMenu")
