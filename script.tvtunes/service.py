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

# Import the common settings
from settings import log
from settings import Settings
from settings import WindowShowing

from backend import TunesBackend


# Class to detect when something in the system has changed
class TvTunesMonitor(xbmc.Monitor):
    def onSettingsChanged(self):
        log("TvTunesMonitor: Notification of settings change received")
        Settings.reloadSettings()


##################################
# Main of the TvTunes Service
##################################
if __name__ == '__main__':
    log("Starting TvTunes Service %s" % __addon__.getAddonInfo('version'))

    # Make sure we have recorded this machines Id
    Settings.setTvTunesId()

    # Check if the settings mean we want to reset the volume on startup
    startupVol = Settings.getStartupVolume()

    if startupVol < 0:
        log("TvTunesService: No Volume Change Required")
    else:
        log("TvTunesService: Setting volume to %s" % startupVol)
        xbmc.executebuiltin('SetVolume(%d)' % startupVol, True)

    # Check if the video info button should be hidden, we do this here as this will be
    # called when the system is loaded, it can then be read by the skin
    # when it comes to draw the button
    WindowShowing.updateHideVideoInfoButton()
    WindowShowing.updateShowOnContextMenu()

    # Make sure the user wants to play themes
    if Settings.isThemePlayingEnabled():
        log("TvTunesService: Theme playing enabled")

        if Settings.isUploadEnabled():
            log("TvTunesService: Launching uploader")
            xbmc.executebuiltin('RunScript(%s)' % os.path.join(__lib__, "upload.py"), False)
        else:
            log("TvTunesService: Uploader not enabled")

        # Create a monitor so we can reload the settings if they change
        systemMonitor = TvTunesMonitor()

        # Start looping to perform the TvTune theme operations
        main = TunesBackend()

        # Start the themes running
        main.runAsAService()

        del main
        del systemMonitor
    else:
        log("TvTunesService: Theme playing disabled")
