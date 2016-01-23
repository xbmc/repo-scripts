# -*- coding: utf-8 -*-
import sys
import os
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
from settings import log

from core import SuitabilityCore


#########################
# Main
#########################
if __name__ == '__main__':
    log("Suitability: Started")

    videoName = xbmc.getInfoLabel("ListItem.Title")

    # If there is no video name available prompt for it
    if videoName in [None, ""]:
        # Prompt the user for the new name
        keyboard = xbmc.Keyboard('', __addon__.getLocalizedString(32032), False)
        keyboard.doModal()

        if keyboard.isConfirmed():
            try:
                videoName = keyboard.getText().decode("utf-8")
            except:
                videoName = keyboard.getText()

    if videoName not in [None, ""]:
        log("Suitability: Movie detected %s" % videoName)
        SuitabilityCore.runForMovie(videoName)
    else:
        log("Suitability: Failed to detect selected video")
        xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001), __addon__.getLocalizedString(32011))

    log("Suitability: Ended")
