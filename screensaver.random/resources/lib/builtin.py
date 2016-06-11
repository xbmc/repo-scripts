# -*- coding: utf-8 -*-
import xbmcgui
import xbmcaddon

# Import the common settings
from settings import log


ADDON = xbmcaddon.Addon(id='screensaver.random')
CWD = ADDON.getAddonInfo('path').decode("utf-8")


class ScreensaverWindow(xbmcgui.WindowXMLDialog):
    DIM_CONTROL = 3002

    def __init__(self, strXMLname, strFallbackPath, dimLevelValue=None):
        self.dimLevel = dimLevelValue
        self.isClosed = False

    # Static method to create the Window class
    @staticmethod
    def createScreensaverWindow(dimLevel):
        return ScreensaverWindow("screensaver-random-main.xml", CWD, dimLevelValue=dimLevel)

    # Called when setting up the window
    def onInit(self):
        xbmcgui.WindowXML.onInit(self)

        # Set the value of the dimming
        if self.dimLevel is not None:
            log("Setting Dim Level to: %s" % self.dimLevel)
            dimControl = self.getControl(ScreensaverWindow.DIM_CONTROL)
            dimControl.setColorDiffuse(self.dimLevel)

    # Handle any activity on the screen, this will result in a call
    # to close the screensaver window
    def onAction(self, action):
        log("Action received: %s" % str(action.getId()))
        self.close()

    # The user clicked on a control
    def onClick(self, control):
        log("OnClick received")
        self.close()
