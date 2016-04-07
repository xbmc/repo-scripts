# -*- coding: utf-8 -*-
import os
import urllib
import traceback
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

# Import the common settings
from resources.lib.settings import log
from resources.lib.settings import Settings
from resources.lib.timer import TimerWindow
from resources.lib.overlay import SleepOverlay

ADDON = xbmcaddon.Addon(id='script.sleep')


# Class to detect when something in the system has changed
class SleepMonitor(xbmc.Monitor):
    def __init__(self):
        self.screensaverActive = False

    def onSettingsChanged(self):
        log("SleepMonitor: Notification of settings change received")
        Settings.reloadSettings()
        # Need to wait a couple of seconds for the changes to work
        # through, reloading the keymap straight away didn't work
        if not self.waitForAbort(2):
            # Once the settings are reloaded, then we need to regenerate the
            # keymap as that may have changes
            keymap = KeyMapCtrl()
            keymap.enableKeymap()
            del keymap

    # Called when the screensaver should be stopped
    def onScreensaverDeactivated(self):
        log("Deactivate Screensaver")
        self.screensaverActive = False

    def onScreensaverActivated(self):
        log("Activate Screensaver")
        self.screensaverActive = True

    def isScreensaverActive(self):
        # Only really care if the shutdown setting is configured
        if not Settings.shutdownOnScreensaver():
            self.screensaverActive = False
        state = self.screensaverActive
        self.screensaverActive = False
        return state


# Player to find out when a track finishes
class SleepPlayer(xbmc.Player):
    def __init__(self, *args, **kwargs):
        self.playbackJustStopped = False
        self.isVideoPlayback = True
        xbmc.Player.__init__(self)

    def onPlayBackEnded(self):
        self.playbackJustStopped = True

    def onPlayBackStarted(self):
        if not self.playbackJustStopped:
            self.isVideoPlayback = self.isPlayingVideo()

    def getAndResetPlaybackEnd(self):
        justStopped = False
        if self.isVideoPlayback:
            justStopped = self.playbackJustStopped
        self.playbackJustStopped = False
        return justStopped


# Handles creating, updating and deleting the key map file
class KeyMapCtrl():
    KEY_MAP_SECTIONS = [
        'global',
        'Home',
        'MyTVChannels',
        'MyTVRecordings',
        'MyTVTimers',
        'MyRadioChannels',
        'MyRadioRecordings',
        'MyRadioTimers',
        'TVGuide',
        'MyFiles',
        'MyMusicPlaylist',
        'MyMusicPlaylistEditor',
        'MyMusicFiles',
        'MyMusicLibrary',
        'FullscreenVideo',
        'VideoTimeSeek',
        'FullscreenInfo',
        'PlayerControls',
        'Visualisation',
        'MusicOSD',
        'VisualisationSettings',
        'VisualisationPresetList',
        'SlideShow',
        'VideoOSD',
        'VideoMenu',
        'MyVideoLibrary',
        'MyVideoFiles',
        'MyVideoPlaylist',
        'MyPictures',
        'MusicInformation',
        'MovieInformation',
        'PictureInfo',
        'Teletext',
        'Favourites',
        'FullscreenLiveTV',
        'FullscreenRadio',
        'PVROSDChannels',
        'PVROSDGuide',
        'FileBrowser',
        'Addon',
        'Programs',
        'Weather'
    ]

    def __init__(self):
        self.keymapLocation = os.path.join(xbmc.translatePath('special://userdata/keymaps'), "sleep_keymap.xml")

    # Creates the keymap with the correct mappings
    def enableKeymap(self):
        # Content to make up the keymap file
        keymapContent = self._getFileContent()

        if keymapContent not in [None, ""]:
            # Now save the new file
            try:
                keymapFile = xbmcvfs.File(self.keymapLocation, 'w')
                keymapFile.write(keymapContent)
                keymapFile.close()
            except:
                log("Sleep: Failed to create & load custom keymap: %s" % traceback.format_exc(), xbmc.LOGERROR)

            # Force a re-load
            xbmc.executebuiltin('Action(reloadkeymaps)')
        else:
            # If there is no keymap set, make sure it is not there
            self.disableKeymap()

    # Removes the keymap so it is no longer active
    def disableKeymap(self):
        if xbmcvfs.exists(self.keymapLocation):
            try:
                xbmcvfs.delete(self.keymapLocation)
                log("Sleep: Removed custom keymap")
            except:
                log("Sleep: Failed to remove & load custom keymap: %s" % traceback.format_exc(), xbmc.LOGERROR)

            # Force a re-load
            xbmc.executebuiltin('Action(reloadkeymaps)')

    # Generates the expected keymap content
    def _getFileContent(self):
        # Get the details of the required keymap
        keymapDetails = Settings.getKeymapData()

        if keymapDetails in [None, ""]:
            return None

        # Create the start of key map
        content = '<keymap>\n'

        for section in KeyMapCtrl.KEY_MAP_SECTIONS:
            content = content + '  <' + section + '>\n'

            # Start with the keyboard commands
            keyboards = self._getKeymapLine(keymapDetails.get('keyboard', []))
            if len(keyboards) > 0:
                content = content + '    <keyboard>\n'
                # Add each of the keyboard values
                for keyboard in keyboards:
                    content = content + keyboard
                content = content + '    </keyboard>\n'

            # Now add the remote commands
            remotes = self._getKeymapLine(keymapDetails.get('remote', []))
            if len(remotes) > 0:
                content = content + '    <remote>\n'
                # Add each of the remotes values
                for remote in remotes:
                    content = content + remote
                content = content + '    </remote>\n'

            content = content + '  </' + section + '>\n'

        # Append the end of the key map
        content = content + '</keymap>\n'

        log("Sleep: Keymap content is %s" % content)
        return content

    # Generates a single line of the keymap
    def _getKeymapLine(self, details):
        # Create the start of key map
        lines = []

        # Add each of the  values
        for detail in details:
            mod = ""
            modList = []
            if detail.get('ctrl', False):
                modList.append('ctrl')
            if detail.get('alt', False):
                modList.append('alt')
            if detail.get('shift', False):
                modList.append('shift')
            if len(modList) > 0:
                mod = ' mod="%s"' % ','.join(modList)

            # Set the format we are using, name or code
            elementNameStart = detail['name']
            elementNameEnd = detail['name']
            if detail.get('code', False):
                elementNameStart = 'key id="%s"' % detail['name']
                elementNameEnd = 'key'
            lines.append('      <%s%s>SetProperty(SleepPrompt, true, 10000)</%s>\n' % (elementNameStart, mod, elementNameEnd))

        return lines


##################################
# Main of the Sleep Service
##################################
if __name__ == '__main__':
    log("Sleep: Service Started")

    keymap = KeyMapCtrl()
    keymap.enableKeymap()

    # Construct the monitor to detect system changes
    monitor = SleepMonitor()
    # Construct the player we use to monitor if a video stopped
    playerMonitor = SleepPlayer()

    secondsUntilSleep = -1
    timerCancelled = True
    timerAfterVideo = False

    # Window used to overlay an image while the timer is running
    overlayWindow = None

    while not monitor.abortRequested():
        showTimerWindow = False
        screensaverTrigger = False

        # Check if we need to prompt the user to enter a new set of sleep values
        sleepPrompt = xbmcgui.Window(10000).getProperty("SleepPrompt")
        if sleepPrompt not in ["", None]:
            xbmcgui.Window(10000).clearProperty("SleepPrompt")
            log("Sleep: Request to display prompt detected")
            showTimerWindow = True
            # Check if were were triggered as a screensaver
            if sleepPrompt.lower() == "screensaver":
                secondsUntilSleep = 1
                screensaverTrigger = True

        # Check if we need to warn the user that the system is about to shut down
        if secondsUntilSleep == Settings.getWarningLength():
            log("Sleep: Nearing sleep time, display dialog")
            showTimerWindow = True

        if timerAfterVideo and playerMonitor.getAndResetPlaybackEnd():
            log("Sleep: Detected playback just stopped, shutting down")
            showTimerWindow = True
            secondsUntilSleep = Settings.getWarningLength()
            timerAfterVideo = False

        # Check if we should shut down if the screensaver starts
        if (monitor.isScreensaverActive() or screensaverTrigger) and (secondsUntilSleep > 0):
            log("Sleep: Screensaver started while timer set, or Sleep Screensaver")
            # Need to wake up the screensaver so we can see the shutdown dialog

            # A bit of a hack, but we need Kodi to think a user is "doing things" so
            # that itstops the screensaver, so we just send the message
            # to open the Context menu - which in our case will do nothing
            # but it does make Kodi think the user has done something
            xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Input.ContextMenu", "id": 1}')

            secondsUntilSleep = 1
            showTimerWindow = True

        videoNeedsResume = False

        if showTimerWindow:
            # Need to display the window using the existing values
            viewer = TimerWindow.createTimerWindow(timerAfterVideo, secondsUntilSleep)

            # Check if we need to pause the video, if we pause it then we actually leave
            # the resume until later - as we might actually be about to exit kodi so there
            # is no point starting the video again, just for it to be stopped
            if Settings.pauseVideoForDialogDisplay() and xbmc.Player().isPlayingVideo():
                log("Sleep: Pausing video to display timer dialog")
                xbmc.Player().pause()
                videoNeedsResume = True

            # If TvTunes was playing, then allow it to continue
            xbmcgui.Window(12000).setProperty("TvTunesContinuePlaying", "True")

            viewer.show()
            # Tidy up any duplicate presses of the remote button before we run
            # the progress
            xbmcgui.Window(10000).clearProperty("SleepPrompt")
            viewer.runProgress()

            # Clear the TvTunes flag
            xbmcgui.Window(12000).clearProperty("TvTunesContinuePlaying")

            # Now read the values entered for the sleep timers
            timerCancelled, timerAfterVideo, secondsUntilSleep = viewer.getTimerValues()
            del viewer

            # Check if the timer has been set and we need to dim the screen
            if Settings.getDimValue() not in [None, "", '00000000']:
                if (timerAfterVideo or (secondsUntilSleep > 0)) and (not timerCancelled):
                    log("Sleep: Dimming screen")
                    if overlayWindow is None:
                        overlayWindow = SleepOverlay.createSleepOverlay()
                    if overlayWindow.isClosed():
                        overlayWindow.show()
                else:
                    if overlayWindow is not None:
                        if not overlayWindow.isClosed():
                            overlayWindow.close()
                        del overlayWindow
                        overlayWindow = None

        elif (not timerCancelled) and (secondsUntilSleep > 0) and Settings.displaySleepReminders():
            # Check if notifications are required
            # Need to notify on set boundaries
            secondsInInterval = Settings.getIntervalLength() * 60
            # Check if we are on a set interval
            if secondsUntilSleep % secondsInInterval == 0:
                label = "%d %s" % (int(secondsUntilSleep / 60), ADDON.getLocalizedString(32106))
                xbmcgui.Dialog().notification(ADDON.getLocalizedString(32001).encode('utf-8'), label.encode('utf-8'), ADDON.getAddonInfo('icon'), 3000, False)

        if secondsUntilSleep > 0:
            # Reduce the remaining timer by one second
            secondsUntilSleep = secondsUntilSleep - 1

        # Check if it is time to exit
        if (not timerCancelled) and (secondsUntilSleep == 0):
            # Check if anything is playing, if so we want to stop it
            if xbmc.Player().isPlaying():
                xbmc.Player().stop()
                log("Sleep: Stopped media playing before shutdown")
            # Using ShutDown will perform the default behaviour that Kodi has in the system settings
            if Settings.getShutdownCommand() == Settings.SHUTDOWN_DEFAULT:
                log("Sleep: Default shutdown started")
                xbmc.executebuiltin("ShutDown")
            elif Settings.getShutdownCommand() == Settings.SHUTDOWN_SCREENSAVER:
                log("Sleep: Screensaver shutdown started")
                xbmc.executebuiltin("ActivateScreensaver")
            elif Settings.getShutdownCommand() == Settings.SHUTDOWN_HTTP:
                url = Settings.getShutdownURL()
                if url in [None, ""]:
                    log("Sleep: Shutdown URL not set")
                else:
                    log("Sleep: Calling shutdown url %s" % url)
                    try:
                        # Call the url, we don't care about the response
                        fp, h = urllib.urlretrieve(url)
                        log(h)
                    except:
                        log("Sleep: Failed to call shutdown url: %s" % traceback.format_exc(), xbmc.LOGERROR)
            elif Settings.getShutdownCommand() == Settings.SHUTDOWN_SCRIPT:
                log("Sleep: Script shutdown started")
                shutdownScript = Settings.getShutdownScript()
                if (shutdownScript in [None, ""]) or (not xbmcvfs.exists(shutdownScript)):
                    log("Sleep: Shutdown Script Invalid")
                    xbmcgui.Dialog().notification(ADDON.getLocalizedString(32001).encode('utf-8'), ADDON.getLocalizedString(32037).encode('utf-8'), ADDON.getAddonInfo('icon'), 5000, False)
                else:
                    xbmc.executebuiltin("RunScript(%s)" % shutdownScript, False)

            secondsUntilSleep = -1
            timerCancelled = True
            timerAfterVideo = False
        elif videoNeedsResume:
            log("Sleep: Resuming video as we paused it for sleep dialog")
            videoNeedsResume = False
            xbmc.Player().pause()

        # Sleep/wait for abort for the correct interval
        if monitor.waitForAbort(1):
            # Abort was requested while waiting
            break

    del playerMonitor
    del monitor

    keymap.disableKeymap()
    del keymap

    log("Sleep: Service Ended")
