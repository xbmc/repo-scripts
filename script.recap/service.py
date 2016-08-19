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
    xbmcgui.Window(10025).setProperty("RecapHideContextMenu", "true")
    xbmcgui.Window(10025).setProperty("RecapPreviousHideContextMenu", "true")

    msg = 'The Recap Addon has been removed from the Official Repo'
    msg2 = 'Recap is now located in the robwebset repository.'
    msg3 = 'See the forum for more information'
    makeRequest = xbmcgui.Dialog().ok('Recap Has Moved', msg, msg2, msg3)
