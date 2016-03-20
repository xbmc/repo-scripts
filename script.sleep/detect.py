# -*- coding: utf-8 -*-
import sys
import os
import xbmc
import xbmcgui
import xbmcaddon

__addon__ = xbmcaddon.Addon(id='script.sleep')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__fanart__ = __addon__.getAddonInfo('fanart')
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__lib__)

# Import the common settings
from settings import log
from settings import Settings


#######################################
# Window to detect a remote key press
#######################################
class DetectWindow(xbmcgui.WindowXMLDialog):
    BACKGROUND_IMAGE = 101
    TEXT_LABEL = 103
    CANCEL_BUTTON = 104

    def __init__(self, *args, **kwargs):
        self.closed = False
        self.buttonCode = None

        xbmcgui.WindowXMLDialog.__init__(self)

    @staticmethod
    def createDetectWindow():
        return DetectWindow("script-sleep-detect.xml", __cwd__)

    # Called when setting up the window
    def onInit(self):
        # Set the labels on the decrease and increase buttons
        imageControl = self.getControl(DetectWindow.BACKGROUND_IMAGE)
        imageControl.setImage(__fanart__)

        xbmcgui.WindowXMLDialog.onInit(self)

    # Handle the close action
    def onAction(self, action):
        ACTION_PREVIOUS_MENU = 10
        ACTION_NAV_BACK = 92
        if (action.getId() == ACTION_PREVIOUS_MENU) or (action.getId() == ACTION_NAV_BACK):
            log("DetectWindow: Close Action received: %s" % str(action.getId()))
            self.close()
        elif action.getButtonCode() not in [None, "", 0]:
            labelControl = self.getControl(DetectWindow.TEXT_LABEL)
            labelControl.setText(__addon__.getLocalizedString(32103))
            self.buttonCode = str(action.getButtonCode())
            log("DetectWindow: Button Code is %s" % self.buttonCode)

            # Need to make a call to the settings to enable the new value
            Settings.setKeymapData(self.buttonCode)

            # Now leave a little time before we continue, the service should pick
            # up the settings change and create a new mapping file
            monitor = xbmc.Monitor()
            monitor.waitForAbort(3)
            del monitor

            self.close()

    def onClick(self, controlID):
        # Play button has been clicked
        if controlID == DetectWindow.CANCEL_BUTTON:
            log("DetectWindow: Close click action received: %d" % controlID)
            self.buttonCode = None
            self.close()

    def close(self):
        log("DetectWindow: Closing window")
        self.closed = True
        xbmcgui.WindowXMLDialog.close(self)

    def getButtonCode(self):
        return self.buttonCode

##################################
# Main of the Sleep Service
##################################
if __name__ == '__main__':
    log("SleepDetect: Configure Started")

    detect = DetectWindow.createDetectWindow()
    detect.doModal()
    del detect

    log("SleepDetect: Configure Complete")
