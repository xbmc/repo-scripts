# -*- coding: utf-8 -*-
import xbmcaddon
import xbmcgui

# Import the common settings
from resources.lib.settings import log
from resources.lib.collector import Collector

ADDON = xbmcaddon.Addon(id='screensaver.random')


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

        xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001), ADDON.getLocalizedString(32103), screensaverList)
    else:
        xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001), ADDON.getLocalizedString(32102))

    log("RandomScreensaver Finished")
