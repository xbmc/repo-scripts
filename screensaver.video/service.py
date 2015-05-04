# -*- coding: utf-8 -*-
import sys
import os
import xbmc
import xbmcaddon


__addon__ = xbmcaddon.Addon(id='screensaver.video')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__lib__)

# Import the common settings
from settings import log
from settings import Settings


##################################
# Main of the TvTunes Service
##################################
if __name__ == '__main__':
    # Check if the settings mean we want to reset the volume on startup
    startupVol = Settings.getStartupVolume()

    if startupVol < 0:
        log("VideoScreensaverService: No Volume Change Required")
    else:
        log("VideoScreensaverService: Setting volume to %s" % startupVol)
        xbmc.executebuiltin('XBMC.SetVolume(%d)' % startupVol, True)
