# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon
import random
import time

# Import the common settings
from resources.lib.settings import log
from resources.lib.settings import Settings
from resources.lib.collector import Collector
from resources.lib.builtin import ScreensaverWindow

ADDON = xbmcaddon.Addon(id='screensaver.random')
ICON = ADDON.getAddonInfo('icon')


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


# Gets the level from the Dim screensaver
def getDimLevel():
    dimLevel = 'AA000000'
    try:
        dimScreensaver = xbmcaddon.Addon(id='screensaver.xbmc.builtin.dim')
        if dimScreensaver not in [None, ""]:
            levelSetting = dimScreensaver.getSetting('level')
            if levelSetting not in [None, ""]:
                log("RandomScreensaver: Detected Dim screensaver level is %s" % levelSetting)
                # The lower the percentage, the darker the screen
                levelValue = int(levelSetting)
                if levelValue == 0:
                    # Completely black
                    dimLevel = 'FF000000'
                elif levelValue < 8:
                    dimLevel = 'EE000000'
                elif levelValue < 15:
                    dimLevel = 'DD000000'
                elif levelValue < 23:
                    dimLevel = 'CC000000'
                elif levelValue < 30:
                    dimLevel = 'BB000000'
                elif levelValue < 38:
                    dimLevel = 'AA000000'
                elif levelValue < 45:
                    dimLevel = '99000000'
                elif levelValue < 53:
                    dimLevel = '88000000'
                elif levelValue < 60:
                    dimLevel = '77000000'
                elif levelValue < 68:
                    dimLevel = '66000000'
                elif levelValue < 75:
                    dimLevel = '55000000'
                elif levelValue < 83:
                    dimLevel = '44000000'
                elif levelValue < 90:
                    dimLevel = '33000000'
                elif levelValue < 96:
                    dimLevel = '22000000'
                elif levelValue < 100:
                    dimLevel = '11000000'
                elif levelValue == 100:
                    # Completely Clear
                    dimLevel = '00000000'
    except:
        log("RandomScreensaver: Failed to find Dim setting, using default 20")

    return dimLevel


##################################
# Main of the Random Screensaver
##################################
if __name__ == '__main__':
    log("RandomScreensaver Starting %s" % ADDON.getAddonInfo('version'))

    screensavers = []

    # Check if the selection is the default Random method
    if Settings.isRandomMode():
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
    else:
        # This is the schedule mode so get the screensaver that was marked as scheduled

        # Get the current time that we are checking the schedule for
        localTime = time.localtime()
        currentTime = (localTime.tm_hour * 60) + localTime.tm_min

        screensaver = Settings.getScheduledScreensaver(currentTime)
        if screensaver in [None, ""]:
            log("RandomScreensaver: No screensaver set for time %d" % currentTime)
        else:
            log("RandomScreensaver: Screensaver for time %d is %s" % (currentTime, screensaver))
            screensavers.append(screensaver)

    # Check to see if we found any non-default screensavers installed
    if len(screensavers) > 0:
        log("RandomScreensaver: Found a total of %d screensavers" % len(screensavers))
        selectedScreensaver = random.randrange(0, len(screensavers), 1)
        log("RandomScreensaver: Launching screensaver: %s" % screensavers[selectedScreensaver])
        # Generate the command to launch the screensaver

        # Check to see if it is either the built in Dim or Black screensaver
        # This can only happen if schedule is being used, but if they are used, then
        # use our own internal Dim or Black as we can not call system screensavers
        if screensavers[selectedScreensaver] in ['screensaver.xbmc.builtin.black', 'screensaver.xbmc.builtin.dim']:
            log("RandomScreensaver: Simulating built-in screensaver: %s" % screensavers[selectedScreensaver])

            # Start the monitor so we can see when the screensaver quits
            exitMon = ScreensaverExitMonitor()

            # A bit of a hack, but we need Kodi to think a user is "doing things" so
            # that it stops the screensaver, so we just send the message
            # to open the Context menu - which in our case will do nothing
            # but it does make Kodi think the user has done something
            xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Input.ContextMenu", "id": 1}')

            # Limit the maximum amount of time to wait for the screensaver to end
            maxWait = 30
            while (not exitMon.isStopScreensaver()) and (maxWait > 0):
                log("RandomScreensaver: still running initial screensaver, waiting for stop")
                xbmc.sleep(100)
                maxWait = maxWait - 1

            del exitMon
            log("RandomScreensaver: Initial screensaver stopped")

            # Default Dim level is Black
            dimLevel = 'FF000000'

            if screensavers[selectedScreensaver] == 'screensaver.xbmc.builtin.dim':
                dimLevel = getDimLevel()

            screensaverWindow = ScreensaverWindow.createScreensaverWindow(dimLevel)
            screensaverWindow.doModal()
            del screensaverWindow
        else:
            cmd = "RunScript(%s,screensaver=True)" % screensavers[selectedScreensaver]
            xbmc.executebuiltin(cmd, True)
    else:
        # If there are no screensavers that can be used for the random screensaver
        # then let the user know
        cmd = 'Notification("{0}", "{1}", 3000, "{2}")'.format(ADDON.getLocalizedString(32001).encode('utf-8'), ADDON.getLocalizedString(32101).encode('utf-8'), ICON)
        xbmc.executebuiltin(cmd)

    log("RandomScreensaver Finished")
