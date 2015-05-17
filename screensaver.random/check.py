# -*- coding: utf-8 -*-
import sys
import os
import xbmc
import xbmcaddon
import xbmcgui


__addon__ = xbmcaddon.Addon(id='screensaver.random')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__lib__)

# Import the common settings
from settings import log
from collector import Collector


#############################################
# Check Operation for the Random Screensaver
#############################################
if __name__ == '__main__':
    log("RandomScreensaver Check Starting")

    # Make the call to find out all the screensaver addons that are installed
    screensavers = Collector.getInstalledScreensavers()

    # Check to see if all the screensavers that have been collected are also
    # able to run as scripts - if they are not, then we can not launch them from
    # a sub-script
    unsupportedScreensavers = []
    if len(screensavers) > 0:
        # Get all the screensavers that can not be launched as a script, because we
        # can not allow those to be chosen
        unsupportedScreensavers = Collector.getUnsupportedScreensavers(screensavers)

    log("Number of unsupported screensavers is %d" % len(unsupportedScreensavers))

    # Check to see if we found any non-default screensavers installed
    if len(unsupportedScreensavers) > 0:
        # Generate the list of unsupported screensavers for display
        screensaverList = ""
        for itemId in unsupportedScreensavers:
            screensaverList = "    %s\n" % itemId

        xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001), __addon__.getLocalizedString(32103), screensaverList)
    else:
        xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001), __addon__.getLocalizedString(32102))

    log("RandomScreensaver Finished")
