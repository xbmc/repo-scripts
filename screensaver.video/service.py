# -*- coding: utf-8 -*-
import os
import xbmc
import xbmcaddon

# Import the common settings
from resources.lib.settings import log
from resources.lib.settings import Settings

ADDON = xbmcaddon.Addon(id='screensaver.video')
CWD = ADDON.getAddonInfo('path').decode("utf-8")


##################################
# Main of the TvTunes Service
##################################
if __name__ == '__main__':
    log("VideoScreensaverService: Startup checks")

    # Check if the settings mean we want to reset the volume on startup
    startupVol = Settings.getStartupVolume()

    if startupVol < 0:
        log("VideoScreensaverService: No Volume Change Required")
    else:
        log("VideoScreensaverService: Setting volume to %s" % startupVol)
        xbmc.executebuiltin('SetVolume(%d)' % startupVol, True)

    # Make sure that the settings have been updated correctly
    Settings.cleanAddonSettings()

    # Check if we should start the screensaver video on startup
    if Settings.isLaunchOnStartup():
        log("VideoScreensaverService: Launching screensaver video on startup")
        xbmc.executebuiltin('RunScript(%s)' % (os.path.join(CWD, "screensaver.py")))
