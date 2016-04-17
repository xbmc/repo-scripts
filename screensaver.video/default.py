# -*- coding: utf-8 -*-
import os
import xbmc
import xbmcaddon
import xbmcgui
import traceback

# Import the common settings
from resources.lib.settings import log
from resources.lib.settings import Settings

ADDON = xbmcaddon.Addon(id='screensaver.video')
CWD = ADDON.getAddonInfo('path').decode("utf-8")


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


##################################
# Main of the Video Screensaver
##################################
if __name__ == '__main__':

    # Only allow one screensaver to run at a time
    if xbmcgui.Window(10000).getProperty("VideoScreensaverStarting") in ["", None]:
        xbmcgui.Window(10000).setProperty("VideoScreensaverStarting", "true")

        # Start the monitor so we can see when the screensaver quits
        exitMon = ScreensaverExitMonitor()

        log("Starting Video Screensaver %s" % ADDON.getAddonInfo('version'))

        # Make a special check to see if and background media is running (e.g. TvTunes)
        # As we want to give that time to stop before we start trying to play the video
        maxBackgroundMediaWait = 400
        okToRunVideoScreensaver = True

        while maxBackgroundMediaWait > 0:
            maxBackgroundMediaWait = maxBackgroundMediaWait - 1
            # If TvTunes is not running then stop waiting
            if xbmcgui.Window(10025).getProperty("PlayingBackgroundMedia") in [None, ""]:
                log("Background media is not playing")
                break
            else:
                log("Background media is currently playing")

            # Check if we have been requested to stop the screensaver
            if exitMon.isStopScreensaver():
                log("Stopping screensaver while waiting for background media to end")
                okToRunVideoScreensaver = False
                break

            xbmc.sleep(10)

        if okToRunVideoScreensaver:
            try:
                # Stop TvTunes trying to start while we load the screensaver
                xbmcgui.Window(10025).setProperty("TvTunesBlocked", "true")

                # Give a little bit of time for everything to shake out before starting the screensaver
                # waiting another few seconds to start a screensaver is not going to make a difference
                # to the user
                xbmc.sleep(1000)

                # Check if media (Music or video) is playing already when the screensaver
                # starts, as the user may want to stop the screensaver running if they are
                # playing music
                if not (xbmc.Player().isPlaying() and Settings.isBlockScreensaverIfMediaPlaying()):
                    # When we are called to start the screensaver we need to immediately stop
                    # the screensaver, this is because we want to play a video file, an action
                    # which in itself will cause the screensaver to stop
                    log("Waking screensaver with call to context menu")
                    xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Input.ContextMenu", "id": 1}')

                    # Limit the maximum amount of time to wait for the screensaver to end
                    maxWait = 30

                    while (not exitMon.isStopScreensaver()) and (maxWait > 0):
                        log("still running default screensaver, waiting for stop")
                        xbmc.sleep(100)
                        maxWait = maxWait - 1

                    log("Default screensaver stopped")

                    # Now we need to launch a new script that will start the video
                    # playing for the screensaver, it will then listen for any action or
                    # activity and stop the video being used as the screensaver
                    log("Running video screensaver in separate thread")
                    xbmc.executebuiltin('RunScript(%s)' % (os.path.join(CWD, "screensaver.py")))
                    # Give the screensaver time to kick in
                    xbmc.sleep(3000)
                else:
                    log("Stopping screensaver as media playing")
                    xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Input.ContextMenu", "id": 1}')

            except:
                log("Failed to start VideoScreensaver: %s" % traceback.format_exc(), xbmc.LOGERROR)

        del exitMon
        xbmcgui.Window(10025).clearProperty("TvTunesBlocked")
        xbmcgui.Window(10000).clearProperty("VideoScreensaverStarting")
    else:
        log("VideoScreensaver already flagged as running")
