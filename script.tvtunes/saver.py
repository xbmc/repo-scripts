# -*- coding: utf-8 -*-
import sys
import os
import xbmc
import xbmcaddon


__addon__ = xbmcaddon.Addon(id='script.tvtunes')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__lib__)

from screensaver import launchScreensaver


##################################
# Main of the TvTunes Screensaver
##################################
if __name__ == '__main__':
    launchScreensaver()
