# -*- coding: utf-8 -*-
import xbmcaddon
import xbmcgui

# Import the common settings
from settings import log
from settings import Settings

ADDON = xbmcaddon.Addon(id='script.pinsentry')
CWD = ADDON.getAddonInfo('path').decode("utf-8")


# Class to set the background while a pin is prompted for
class Background(xbmcgui.WindowXML):
    BACKGOUND_IMAGE_ID = 3004

    @staticmethod
    def createBackground():
        # Check to see if the background is enabled
        if not Settings.isDisplayBackground():
            return None
        return Background("pinsentry-background.xml", CWD)

    def onInit(self):
        xbmcgui.WindowXMLDialog.onInit(self)

        # Get the background image to be used
        bgImage = Settings.getBackgroundImage()

        if bgImage is not None:
            log("Background: Setting background image to %s" % bgImage)
            bgImageCtrl = self.getControl(Background.BACKGOUND_IMAGE_ID)
            bgImageCtrl.setImage(bgImage)
