# -*- coding: utf-8 -*-
import sys
import xbmc
import xbmcaddon
import xbmcgui

# Import the common settings
from resources.lib.settings import log
from resources.lib.settings import Settings

ADDON = xbmcaddon.Addon(id='screensaver.weather')
CWD = ADDON.getAddonInfo('path').decode("utf-8")


# Window to overlay the Weather screen
class WeatherScreen(xbmcgui.WindowXMLDialog):
    DIM_CONTROL = 3002

    def __init__(self, strXMLname, strFallbackPath):
        self.isClosedFlag = False
        self.ignoreContextMenuAction = False

    @staticmethod
    def createWeatherScreen():
        return WeatherScreen("screensaver-weather-main.xml", CWD)

    # Called when setting up the window
    def onInit(self):
        xbmcgui.WindowXML.onInit(self)

        # Set the value of the dimming for the video
        dimLevel = Settings.getDimValue()
        if dimLevel is not None:
            log("WeatherScreen: Setting Dim Level to: %s" % dimLevel)
            dimControl = self.getControl(WeatherScreen.DIM_CONTROL)
            dimControl.setColorDiffuse(dimLevel)

    # Handle any activity on the screen, this will result in a call
    # to close the screensaver window
    def onAction(self, action):
        log("WeatherScreen: Action received %s" % str(action.getId()))

        # Check if we have been told to ignore a context menu action
        if self.ignoreContextMenuAction and (action.getId() == 117):
            log("WeatherScreen: Ignoring context menu call")
            # Only want to ignore one, so reset the flag
            self.ignoreContextMenuAction = False
            return

        # For any action we want to close, as that means activity
        self.close()

    # The user clicked on a control
    def onClick(self, control):
        log("WeatherScreen: OnClick received")
        self.close()

    def close(self):
        log("WeatherScreen: Closing window")
        self.isClosedFlag = True
        xbmcgui.WindowXML.close(self)

    def isClosed(self):
        return self.isClosedFlag

    def ignoreNextContextMenu(self):
        self.ignoreContextMenuAction = True


##################################
# Main of the Weather Screensaver
##################################
if __name__ == '__main__':
    log("WeatherScreensaver: Monitor started")

    backRequired = False
    try:
        if len(sys.argv) > 1:
            if sys.argv[1].lower() == 'true':
                backRequired = True
    except:
        log("WeatherScreensaver: Error checking for back argument")

    log("WeatherScreensaver: Back required is %s" % str(backRequired))

    if xbmc.getCondVisibility("Window.IsVisible(weather)"):
        log("WeatherScreensaver: Waiting for key stroke")
        # Display the window that will check for the need to end the screensaver and
        # return to the previous page
        weather = WeatherScreen.createWeatherScreen()
        weather.show()

        # Make sure that we stop the screensaver coming in, the minimum value
        # for the screensaver is 1 minute - so set at 40 seconds to keep active
        stopScreensaver = 40000
        sleepInterval = 100

        while (not weather.isClosed()) and (not xbmc.abortRequested):
            xbmc.sleep(sleepInterval)
            stopScreensaver = stopScreensaver - sleepInterval
            if stopScreensaver < sleepInterval:
                # A bit of a hack, but we need Kodi to think a user is "doing things" so
                # that it does not start the screensaver, so we just send the message
                # to open the Context menu - which in our case will do nothing
                # but it does make Kodi think the user has done something

                # We do not want the context menu call to result in the Weather screensaver
                # thinking there is user activity and exiting, so we need to let the
                # window control know to ignore this context menu message
                weather.ignoreNextContextMenu()
                xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Input.ContextMenu", "id": 1}')
                stopScreensaver = 40000

        del weather

        if backRequired:
            log("WeatherScreensaver: Navigating to previous page from before weather displayed")
            xbmc.executebuiltin("Action(back)")
    else:
        log("WeatherScreensaver: Weather screen not visible")

    log("WeatherScreensaver: Monitor Finished")
