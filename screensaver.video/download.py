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
from downloader import Downloader

################################################
# Main of the Video Screensaver Download Option
#################################################
if __name__ == '__main__':
    log("Call to download standard videos")

    # Force the video selection type before we begin to ensure
    # we show the custom type when we finish
    Settings.setVideoSelectionPredefined()

    download = Downloader()

    (selectId, videoLocation) = download.showSelection()

    log("Setting new video location to: %s" % videoLocation)

    # Check if we are using a directory will multiple videos
    # or just a single video file
    if selectId is None:
        log("Download selection Cancelled")
    elif selectId == -1:
        Settings.setScreensaverFolder(videoLocation)
    else:
        # Now set the path in the video dialog
        Settings.setScreensaverVideo(videoLocation)

    if selectId is not None:
        log("Setting new video preselect to: %d" % selectId)
        Settings.setPresetVideoSelected(selectId)

    log("Finished call to download standard videos")
    del download
