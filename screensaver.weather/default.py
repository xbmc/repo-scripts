# -*- coding: utf-8 -*-
import sys
import os
import xbmc
import xbmcaddon

__addon__ = xbmcaddon.Addon(id='screensaver.weather')
__icon__ = __addon__.getAddonInfo('icon')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__lib__)

# Import the common settings
from settings import log


# Monitor class to handle events like the screensaver deactivating
class ScreensaverExitMonitor(xbmc.Monitor):
    def __init__(self):
        self.stopScreensaver = False

    # Called when the screensaver should be stopped
    def onScreensaverDeactivated(self):
        log("Deactivate Screensaver")
        self.stopScreensaver = True

    def onScreensaverActivated(self):
        log("Activate Screensaver")
        self.stopScreensaver = False

    def isStopScreensaver(self):
        return self.stopScreensaver


##################################
# Main of the Weather Screensaver
##################################
if __name__ == '__main__':
    log("WeatherScreensaver Starting %s" % __addon__.getAddonInfo('version'))

    # Start the monitor so we can see when the screensaver quits
    exitMon = ScreensaverExitMonitor()

    # Do something to stop the screensaver and see if we need to navigate
    # to the weather screen, or if it is already showing

    # A bit of a hack, but we need Kodi to think a user is "doing things" so
    # that itstops the screensaver, so we just send the message
    # to open the Context menu - which in our case will do nothing
    # but it does make Kodi think the user has done something
    xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Input.ContextMenu", "id": 1}')

    # Limit the maximum amount of time to wait for the screensaver to end
    maxWait = 30
    while (not exitMon.isStopScreensaver()) and (maxWait > 0):
        log("WeatherScreensaver: still running initial screensaver, waiting for stop")
        xbmc.sleep(100)
        maxWait = maxWait - 1

    del exitMon
    log("WeatherScreensaver: Initial screensaver stopped")

    # Now it is safe to check to see if the Weather screen is showing
    # If we checked before the screensaver was stopped then it would think
    # the active window was the screensaver, rather than the weather
    backRequired = 'true'
    if not xbmc.getCondVisibility("Window.IsVisible(weather)"):
        log("WeatherScreensaver: Navigating to weather screen")

        # Load the screensaver window
        xbmc.executebuiltin("ActivateWindow(Weather)", True)
    else:
        log("WeatherScreensaver: Weather screen already displayed")
        backRequired = 'false'

    # Give a little bit of time for everything to shake out before starting the screensaver
    # waiting another few seconds to start a screensaver is not going to make a difference
    # to the user
    maxWait = 30
    while (not xbmc.abortRequested) and (not xbmc.getCondVisibility("Window.IsVisible(weather)")) and (maxWait > 0):
        log("WeatherScreensaver: waiting for weather to load")
        xbmc.sleep(100)
        maxWait = maxWait - 1

    xbmc.executebuiltin('RunScript(%s,%s)' % (os.path.join(__cwd__, "monitor.py"), backRequired))

    log("WeatherScreensaver Finished")
