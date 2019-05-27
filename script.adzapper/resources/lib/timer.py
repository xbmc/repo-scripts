# -*- coding: utf-8 -*-
import xbmc
import xbmcgui
import xbmcaddon

# Import the common settings
from settings import log
from settings import Settings

ADDON = xbmcaddon.Addon(id='script.adzapper')
CWD = ADDON.getAddonInfo('path').decode("utf-8")


#######################################
# Window to display the shutdown timer
#######################################
class TimerWindow(xbmcgui.WindowXMLDialog):
    TEXT_TIME_LABEL = 102
    TEXT_CHANNEL_LABEL = 103	
    PROGRESS_BAR = 201
    DECREASE_BUTTON = 301
    INCREASE_BUTTON = 302
    CANCEL_BUTTON = 303

    def __init__(self, *args, **kwargs):
        self.cancel = False
        self.closed = False

        self.rezapTime = kwargs.get('secondsUntilRezap', 0)
        self.channelName = kwargs.get('channelName', 0)		

        xbmcgui.WindowXMLDialog.__init__(self)

    @staticmethod
    def createTimerWindow(channelName='',secondsUntilRezap=0):
        return TimerWindow("script-adzapper-dialog.xml", CWD, secondsUntilRezap=secondsUntilRezap, channelName=channelName)

    # Called when setting up the window
    def onInit(self):
    
        # write channelName to gui
        labelChannel = self.getControl(TimerWindow.TEXT_CHANNEL_LABEL)
        labelChannel.setText(self.channelName)        

        # timer disabled?
        if self.rezapTime == -1:
			# if self.rezapTime = -1 timer is disabled and should be enabled to default time
            labelControl = self.getControl(TimerWindow.TEXT_TIME_LABEL)
            # Set the time remaining to disabled
            self.rezapTime = (Settings.getStartLength() * 60)
            self._setRemainingTimeMessage(self.rezapTime)
        elif self.rezapTime > Settings.getWarningLength():
            # Not displaying the rezap warning, so display the time remaining
            self._setRemainingTimeMessage(self.rezapTime)
        else:
            # Default message it that we are about to rezap
            labelControl = self.getControl(TimerWindow.TEXT_TIME_LABEL)
            labelControl.setText(ADDON.getLocalizedString(32101))

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
            self.rezapTime = -1
            self.cancel = True
            self.close()
        elif controlID == TimerWindow.INCREASE_BUTTON:
            log("TimerWindow: Extend click action received: %d" % controlID)
            if self.rezapTime < 0:
                self.rezapTime = 0
            self.rezapTime = self.rezapTime + (Settings.getIntervalLength() * 60)
            # If the user goes over the maximum time, set it as disabled
            if self.rezapTime > (Settings.getMaxTimerLength() * 60):
                self.rezapTime = -1
            self._setRemainingTimeMessage(self.rezapTime)
        elif controlID == TimerWindow.DECREASE_BUTTON:
            log("TimerWindow: Decrease click action received: %d" % controlID)
            if self.rezapTime < 0:
                self.rezapTime = 0
            self.rezapTime = self.rezapTime - (Settings.getIntervalLength() * 60)
            # Switching below zero is disabling
            if self.rezapTime < 1:
                self.rezapTime = -1
            self._setRemainingTimeMessage(self.rezapTime)

    def close(self):
        log("TimerWindow: Closing window")
        self.closed = True
        xbmcgui.WindowXMLDialog.close(self)

    def runProgress(self):
        log("TimerWindow: Running progress bar")
        previousRezapTime = self.rezapTime
        progressBar = self.getControl(TimerWindow.PROGRESS_BAR)
        i = 0
        processingTime = 0
        warningLength = Settings.getWarningLength() * 10
        while (i < warningLength) and (not xbmc.abortRequested):
            # Check if the user has pushed the remote button again, that is the same
            # as performing the add time operation
            if xbmcgui.Window(10000).getProperty("ADZapperPrompt") not in ["", None]:
                xbmcgui.Window(10000).clearProperty("ADZapperPrompt")
                log("Request to display prompt detected")
                self.onClick(TimerWindow.INCREASE_BUTTON)

            # If the user has extended the time give them another 3 second
            if previousRezapTime != self.rezapTime:
                previousRezapTime = self.rezapTime
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
        if (self.rezapTime > 3) and (processingTime > 10):
            self.rezapTime = self.rezapTime - int(processingTime / 10)
            if self.rezapTime < 0:
                self.rezapTime = 0

    # Get all the timer values
    def getTimerValues(self):
        log("TimerWindow: Timer Values: Cancel=%s, RezapTime=%d" % (str(self.cancel), self.rezapTime))
        return self.cancel, self.rezapTime

    # Puts the time remaining on the text section of the screen
    def _setRemainingTimeMessage(self, remainingSeconds):
        labelControl = self.getControl(TimerWindow.TEXT_TIME_LABEL)
        label = ""
        if remainingSeconds < 1:
            # Set label to disabled
            label = ADDON.getLocalizedString(32104)
        else:
            # Convert the time to minutes, making sure it is at least one
            remainingMinutes = int((remainingSeconds + 29) / 60)
            log("TimerWindow: Converted %d seconds into %d minutes" % (remainingSeconds, remainingMinutes))
            label = "%d %s" % (remainingMinutes, ADDON.getLocalizedString(32103))
        labelControl.setText(label)
