# -*- coding: utf-8 -*-
import xbmcgui

# Import the common settings
from resources.lib.settings import log


#########################
# Main
#########################
if __name__ == '__main__':
    log("PinSentry: Started Screensaver")

    # The service will be waiting for the variable to be set, and when set
    # will display the PinSentry dialog
    xbmcgui.Window(10000).setProperty("PinSentryPrompt", "true")
