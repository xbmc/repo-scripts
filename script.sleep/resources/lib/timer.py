# -*- coding: utf-8 -*-
import xbmc
import xbmcgui
import xbmcaddon

# Import the common settings
from settings import log
from settings import Settings

ADDON = xbmcaddon.Addon(id='script.sleep')
CWD = ADDON.getAddonInfo('path').decode("utf-8")


#######################################
# Window to display the shutdown timer
#######################################
class TimerWindow(xbmcgui.WindowXMLDialog):
    TEXT_LABEL = 102
    PROGRESS_BAR = 201
    DECREASE_BUTTON = 301
    INCREASE_BUTTON = 302
    VIDEO_END_BUTTON = 303
    CANCEL_BUTTON = 304

    def __init__(self, *args, **kwargs):
        self.onVideoEnd = kwargs.get('onVideoEnd', False)
        self.cancel = False
        self.closed = False

        self.sleepTime = kwargs.get('secondsUntilSleep', 0)

        xbmcgui.WindowXMLDialog.__init__(self)

    @staticmethod
    def createTimerWindow(onVideoEnd=False, secondsUntilSleep=0):
        return TimerWindow("script-sleep-dialog.xml", CWD, onVideoEnd=onVideoEnd, secondsUntilSleep=secondsUntilSleep)

    # Called when setting up the window
    def onInit(self):
        # If this is the initial setup then we need to change the message
        # to show no value is currently set and not display the progress bar
        if self.sleepTime == -1:
            # If the current value set is the end of video, need to show that
            labelControl = self.getControl(TimerWindow.TEXT_LABEL)
            if self.onVideoEnd:
                labelControl.setText(ADDON.getLocalizedString(32107))
            else:
                # Set the time remaining to disabled
                self._setRemainingTimeMessage(self.sleepTime)
        elif self.sleepTime > Settings.getWarningLength():
            # Not displaying the shutdown warning, so display the time remaining
            self._setRemainingTimeMessage(self.sleepTime)
        else:
            # Default message it that we are about to shut down
            labelControl = self.getControl(TimerWindow.TEXT_LABEL)
            labelControl.setText(ADDON.getLocalizedString(32104))

        # Set the labels on the decrease and increase buttons
        decreaseControl = self.getControl(TimerWindow.DECREASE_BUTTON)
        decreaseLabel = "-%d" % Settings.getIntervalLength()
        decreaseControl.setLabel(decreaseLabel)

        increaseControl = self.getControl(TimerWindow.INCREASE_BUTTON)
        increaseLabel = "+%d" % Settings.getIntervalLength()
        increaseControl.setLabel(increaseLabel)

        xbmcgui.WindowXMLDialog.onInit(self)

    # Handle the close action
    def onAction(self, action):
        ACTION_PREVIOUS_MENU = 10
        ACTION_NAV_BACK = 92
        if (action.getId() == ACTION_PREVIOUS_MENU) or (action.getId() == ACTION_NAV_BACK):
            log("TimerWindow: Close Action received: %s" % str(action.getId()))
            self.close()

    def onClick(self, controlID):
        # Play button has been clicked
        if controlID == TimerWindow.CANCEL_BUTTON:
            log("TimerWindow: Close click action received: %d" % controlID)
            self.sleepTime = -1
            self.onVideoEnd = False
            self.cancel = True
            self.close()
        elif controlID == TimerWindow.INCREASE_BUTTON:
            log("TimerWindow: Extend click action received: %d" % controlID)
            self.onVideoEnd = False
            if self.sleepTime < 0:
                self.sleepTime = 0
            self.sleepTime = self.sleepTime + (Settings.getIntervalLength() * 60)
            # If the user goes over the maximum time, set it as disabled
            if self.sleepTime > (Settings.getMaxSleepTime() * 60):
                self.sleepTime = -1
            self._setRemainingTimeMessage(self.sleepTime)
        elif controlID == TimerWindow.DECREASE_BUTTON:
            log("TimerWindow: Decrease click action received: %d" % controlID)
            self.onVideoEnd = False
            if self.sleepTime < 0:
                self.sleepTime = 0
            self.sleepTime = self.sleepTime - (Settings.getIntervalLength() * 60)
            # Switching below zero is disabling
            if self.sleepTime < 1:
                self.sleepTime = -1
            self._setRemainingTimeMessage(self.sleepTime)
        elif controlID == TimerWindow.VIDEO_END_BUTTON:
            log("TimerWindow: Video End click action received: %d" % controlID)
            self.sleepTime = -1
            self.onVideoEnd = True
            self.close()

    def close(self):
        log("TimerWindow: Closing window")
        self.closed = True
        xbmcgui.WindowXMLDialog.close(self)

    def runProgress(self):
        log("TimerWindow: Running progress bar")
        previousSleepTime = self.sleepTime
        previousOnVideoEnd = self.onVideoEnd
        progressBar = self.getControl(TimerWindow.PROGRESS_BAR)
        i = 0
        processingTime = 0
        warningLength = Settings.getWarningLength() * 10
        while (i < warningLength) and (not xbmc.abortRequested):
            # Check if the user has pushed the remote button again, that is the same
            # as performing the add time operation
            if xbmcgui.Window(10000).getProperty("SleepPrompt") not in ["", None]:
                xbmcgui.Window(10000).clearProperty("SleepPrompt")
                log("Sleep: Request to display prompt detected")
                self.onClick(TimerWindow.INCREASE_BUTTON)

            # Check if the user wants to stop when the next video ends
            if not previousOnVideoEnd and self.onVideoEnd:
                processingTime = 0
                break

            # If the user has extended the time give them another 3 second
            if previousSleepTime != self.sleepTime:
                previousSleepTime = self.sleepTime
                processingTime = 0
                i = 0
                # Set the progress bar to twice the normal speed
                warningLength = Settings.getWarningLength() * 5

            # Move the progress bar on
            i = i + 1
            percentVal = int(float(float(i) / warningLength) * 100)
            if not self.closed:
                progressBar.setPercent(percentVal)
                xbmc.sleep(100)
                processingTime = processingTime + 1

        # Now take off the time that we have been in the progress loop
        if (self.sleepTime > 3) and (processingTime > 10):
            self.sleepTime = self.sleepTime - int(processingTime / 10)
            if self.sleepTime < 0:
                self.sleepTime = 0

    # Get all the timer values
    def getTimerValues(self):
        log("TimerWindow: Timer Values: Cancel=%s, OnVideoEnd=%s, SleepTime=%d" % (str(self.cancel), str(self.onVideoEnd), self.sleepTime))
        return self.cancel, self.onVideoEnd, self.sleepTime

    # Puts the time remaining on the text section of the screen
    def _setRemainingTimeMessage(self, remainingSeconds):
        labelControl = self.getControl(TimerWindow.TEXT_LABEL)
        label = ""
        if remainingSeconds < 1:
            # Set label to disabled
            label = ADDON.getLocalizedString(32108)
        else:
            # Convert the time to minutes, making sure it is at least one
            remainingMinutes = int((remainingSeconds + 29) / 60)
            log("TimerWindow: Converted %d seconds into %d minutes" % (remainingSeconds, remainingMinutes))
            label = "%d %s" % (remainingMinutes, ADDON.getLocalizedString(32106))
        labelControl.setText(label)
