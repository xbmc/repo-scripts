# -*- coding: utf-8 -*-
import sys
import os
import xbmc
import xbmcaddon
import xbmcgui
import traceback


__addon__ = xbmcaddon.Addon(id='screensaver.video')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__lib__)

# Import the common settings
from settings import log
from settings import Settings


# Monitor class to handle events like the screensaver deactivating
class ExitMonitor(xbmc.Monitor):
    stopScreensaver = False

    # Called when the screensaver should be stopped
    def onScreensaverDeactivated(self):
        log("Deactivate Screensaver")
        ExitMonitor.stopScreensaver = True


##################################
# Main of the Video Screensaver
##################################
if __name__ == '__main__':

    # Only allow one screensaver to run at a time
    alreadyRunning = xbmcgui.Window(10000).getProperty("VideoScreensaverStarting")
    if alreadyRunning in ["", None]:
        xbmcgui.Window(10000).setProperty("VideoScreensaverStarting", "true")

        # Make a special check to see if TvTunes is running - as we want to give that time
        # to stop before we start trying to play the video
        maxTvTunesWait = 40
        while maxTvTunesWait > 0:
            maxTvTunesWait = maxTvTunesWait - 1
            # If TvTunes is not running then stop waiting
            if xbmcgui.Window(10025).getProperty("TvTunesIsRunning") in [None, ""]:
                break
            xbmc.sleep(100)

        try:
            # Stop TvTunes trying to start while we load the screensaver
            xbmcgui.Window(10025).setProperty("TvTunesIsRunning", "VideoScreensaver")

            # Give a little bit of time for everything to shake out before starting the screensaver
            # waiting another few seconds to start a screensaver is not going to make a difference
            # to the user
            xbmc.sleep(1000)

            # Check if media (Music or video) is playing already when the screensaver
            # starts, as the user may want to stop the screensaver running if they are
            # playing music
            if not (xbmc.Player().isPlaying() and Settings.isBlockScreensaverIfMediaPlaying()):
                # Start the monitor so we can see when the screensaver quits
                exitMon = ExitMonitor()
                # When we are called to start the screensaver we need to immediately stop
                # the screensaver, this is because we want to play a video file, an action
                # which in itself will cause the screensaver to stop
                log("Waking screensaver with call to context menu")
                xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Input.ContextMenu", "id": 1}')

                # Limit the maximum amount of time to wait for the screensaver to end
                maxWait = 30

                while (not ExitMonitor.stopScreensaver) and (maxWait > 0):
                    log("still running default screensaver, waiting for stop")
                    xbmc.sleep(100)
                    maxWait = maxWait - 1

                del exitMon
                log("Default screensaver stopped")

                # Now we need to launch a new script that will start the video
                # playing for the screensaver, it will then listen for any action or
                # activity and stop the video being used as the screensaver
                log("Running video screensaver in separate thread")
                xbmc.executebuiltin('XBMC.RunScript(%s)' % (os.path.join(__cwd__, "screensaver.py")))
                # Give the screensaver time to kick in
                xbmc.sleep(3000)
            else:
                log("Stopping screensaver as media playing")
                xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Input.ContextMenu", "id": 1}')

        except:
            log("Failed to start VideoScreensaver: %s" % traceback.format_exc(), xbmc.LOGERROR)

        xbmcgui.Window(10025).clearProperty("TvTunesIsRunning")
        xbmcgui.Window(10000).clearProperty("VideoScreensaverStarting")
    else:
        log("VideoScreensaver already flagged as running")
