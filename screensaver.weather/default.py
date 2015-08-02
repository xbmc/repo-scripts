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


##################################
# Main of the Weather Screensaver
##################################
if __name__ == '__main__':
    log("WeatherScreensaver Starting %s" % __addon__.getAddonInfo('version'))

    # Check if the weather weather is already showing, if so we do not need
    # to change the currently active window
    if not xbmc.getCondVisibility("Window.IsVisible(weather)"):
        log("WeatherScreensaver: Navigating to weather screen")
        # Activating a window will actually stop the screensaver, so we will
        # need to check for any movement ourselves and handle that
        xbmc.executebuiltin("ActivateWindow(Weather)", True)

        xbmc.executebuiltin('RunScript(%s)' % (os.path.join(__cwd__, "monitor.py")))
    else:
        log("WeatherScreensaver: Already showing weather screen")

    log("WeatherScreensaver: Leaving initial script")
