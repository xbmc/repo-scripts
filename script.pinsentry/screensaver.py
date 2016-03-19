# -*- coding: utf-8 -*-
import sys
import os
import xbmc
import xbmcgui
import xbmcaddon


__addon__ = xbmcaddon.Addon(id='script.pinsentry')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import log


#########################
# Main
#########################
if __name__ == '__main__':
    log("PinSentry: Started Screensaver")

    # The service will be waiting for the variable to be set, and when set
    # will display the PinSentry dialog
    xbmcgui.Window(10000).setProperty("PinSentryPrompt", "true")
