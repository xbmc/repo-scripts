# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon
import random

# Import the common settings
from resources.lib.settings import log
from resources.lib.settings import Settings
from resources.lib.collector import Collector

ADDON = xbmcaddon.Addon(id='screensaver.random')
ICON = ADDON.getAddonInfo('icon')


##################################
# Main of the Random Screensaver
##################################
if __name__ == '__main__':
    log("RandomScreensaver Starting %s" % ADDON.getAddonInfo('version'))

    # Make the call to find out all the screensaver addons that are installed
    screensavers = Collector.getInstalledScreensavers()

    # Get the list of excluded screensavers
    if len(screensavers) > 0:
        excludedScreensavers = Settings.getExcludedScreensavers()

        # Reduce the screensaver list to the ones not in the exclude list
        if len(excludedScreensavers) > 0:
            log("RandomScreensaver: Screensavers to exclude are %s" % excludedScreensavers)
            screensavers = [item for item in screensavers if item not in excludedScreensavers]

    # Check to see if all the screensavers that have been collected are also
    # able to run as scripts - if they are not, then we can not launch them from
    # a sub-script
    if len(screensavers) > 0:
        # Get all the screensavers that can not be launched as a script, because we
        # can not allow those to be chosen
        unsupportedScreensavers = Collector.getUnsupportedScreensavers(screensavers)

        # Remove the unsupported screensaver addons
        if len(unsupportedScreensavers) > 0:
            screensavers = [item for item in screensavers if item not in unsupportedScreensavers]

    # Check to see if we found any non-default screensavers installed
    if len(screensavers) > 0:
        log("RandomScreensaver: Found a total of %d screensavers" % len(screensavers))
        selectedScreensaver = random.randrange(0, len(screensavers), 1)
        log("RandomScreensaver: Launching screensaver: %s" % screensavers[selectedScreensaver])
        # Generate the command to launch the screensaver
        cmd = "RunScript(%s,screensaver=True)" % screensavers[selectedScreensaver]
        xbmc.executebuiltin(cmd, True)
    else:
        # If there are no screensavers that can be used for the random screensaver
        # then let the user know
        cmd = 'Notification("{0}", "{1}", 3000, "{2}")'.format(ADDON.getLocalizedString(32001).encode('utf-8'), ADDON.getLocalizedString(32101).encode('utf-8'), ICON)
        xbmc.executebuiltin(cmd)

    log("RandomScreensaver Finished")
