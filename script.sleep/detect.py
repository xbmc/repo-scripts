# -*- coding: utf-8 -*-
import xbmc
import xbmcgui
import xbmcaddon

# Import the common settings
from resources.lib.settings import log
from resources.lib.settings import Settings

ADDON = xbmcaddon.Addon(id='script.sleep')
CWD = ADDON.getAddonInfo('path').decode("utf-8")


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
        return DetectWindow("script-sleep-detect.xml", CWD)

    # Called when setting up the window
    def onInit(self):
        # Set the labels on the decrease and increase buttons
        imageControl = self.getControl(DetectWindow.BACKGROUND_IMAGE)
        imageControl.setImage(ADDON.getAddonInfo('fanart'))

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
            labelControl.setText(ADDON.getLocalizedString(32103))
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
