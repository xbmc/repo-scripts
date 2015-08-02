# -*- coding: utf-8 -*-
import sys
import os
import xbmc
import xbmcaddon
import xbmcgui

__addon__ = xbmcaddon.Addon(id='screensaver.weather')
__icon__ = __addon__.getAddonInfo('icon')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__lib__)

# Import the common settings
from settings import log
from settings import Settings


# Window to overlay the Weather screen
class WeatherScreen(xbmcgui.WindowXMLDialog):
    DIM_CONTROL = 3002

    def __init__(self, strXMLname, strFallbackPath):
        pass

    @staticmethod
    def createWeatherScreen():
        return WeatherScreen("screensaver-weather-main.xml", __cwd__)

    # Called when setting up the window
    def onInit(self):
        xbmcgui.WindowXML.onInit(self)

        # Set the value of the dimming for the video
        dimLevel = Settings.getDimValue()
        if dimLevel is not None:
            log("Setting Dim Level to: %s" % dimLevel)
            dimControl = self.getControl(WeatherScreen.DIM_CONTROL)
            dimControl.setColorDiffuse(dimLevel)

    # Handle any activity on the screen, this will result in a call
    # to close the screensaver window
    def onAction(self, action):
        log("Action received")
        # For any action we want to close, as that means activity
        self.close()

    # The user clicked on a control
    def onClick(self, control):
        log("OnClick received")
        self.close()


##################################
# Main of the Weather Screensaver
##################################
if __name__ == '__main__':
    log("WeatherScreensaver waiting for activity to return")

    if xbmc.getCondVisibility("Window.IsVisible(weather)"):
        log("WeatherScreensaver: Waiting for key stroke")
        # Display the window that will check for the need to end the screensaver and
        # return to the previous page
        weather = WeatherScreen.createWeatherScreen()
        weather.doModal()
        del weather

        log("WeatherScreensaver: Navigating to previous page from before weather displayed")
        xbmc.executebuiltin("Action(back)")
    else:
        log("WeatherScreensaver: Weather screen not visible")

    log("WeatherScreensaver Finished")
