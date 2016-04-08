# -*- coding: utf-8 -*-
import xbmcaddon
import xbmcgui

# Import the common settings
from settings import log
from settings import Settings

ADDON = xbmcaddon.Addon(id='script.sleep')
CWD = ADDON.getAddonInfo('path').decode("utf-8")


# Window to overlay the Weather screen
class SleepOverlay(xbmcgui.WindowXMLDialog):
    IMAGE_CONTROL = 3002

    def __init__(self, strXMLname, strFallbackPath):
        self.isClosedFlag = True

    @staticmethod
    def createSleepOverlay():
        return SleepOverlay("script-sleep-overlay.xml", CWD)

    # Called when setting up the window
    def onInit(self):
        xbmcgui.WindowXML.onInit(self)

        # Set the value of the dimming for the screen
        dimLevel = Settings.getDimValue()
        if dimLevel is not None:
            log("SleepOverlay: Setting Dim Level to: %s" % dimLevel)
            dimControl = self.getControl(SleepOverlay.IMAGE_CONTROL)
            dimControl.setColorDiffuse(dimLevel)

    # Handle any activity on the screen, this will result in a call
    # to close the screensaver window
    def onAction(self, action):
        log("SleepOverlay: Action received %s" % str(action.getId()))

        # For any action we want to close, as that means activity
        self.close()

    # The user clicked on a control
    def onClick(self, control):
        log("SleepOverlay: OnClick received")
        self.close()

    def close(self):
        log("SleepOverlay: Closing window")
        self.isClosedFlag = True
        xbmcgui.WindowXML.close(self)

    def isClosed(self):
        return self.isClosedFlag

    def show(self):
        self.isClosedFlag = False
        xbmcgui.WindowXML.show(self)
