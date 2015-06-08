# -*- coding: utf-8 -*-
import sys
import os
import xbmc
import xbmcaddon
import xbmcgui


__addon__ = xbmcaddon.Addon(id='script.pinsentry')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__lib__)

# Import the common settings
from settings import log
from settings import Settings

from numberpad import NumberPad


##################################
# Main of the PinSentry Setter
##################################
if __name__ == '__main__':
    log("Starting Pin Sentry Setter")

    # Before setting the pin we need to ensure that all dialog boxes are closed
    xbmc.executebuiltin("Dialog.Close(all, true)", True)

    okToChangePin = True

    # Check if the pin is already set, if it is, then we need to prompt for that first
    # before we allow the user to just change it
    if Settings.isPinSet():
        log("SetPin: Existing pin set, prompting for it")
        # Prompt the user for the pin
        numberpad = NumberPad.createNumberPad(32105)
        numberpad.doModal()

        # Get the code that the user entered
        enteredPin = numberpad.getPin()
        del numberpad

        if not Settings.isPinCorrect(enteredPin):
            log("SetPin: Incorrect Existing Pin Entered")
            okToChangePin = False
            xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001).encode('utf-8'), __addon__.getLocalizedString(32104).encode('utf-8'))
        else:
            log("SetPin: Correct Existing Pin Entered")

    # If we are OK to change the pin, prompt the user
    if okToChangePin:
        # Prompt the user for the pin
        numberpad = NumberPad.createNumberPad(32106)
        numberpad.doModal()

        # Get the code that the user entered
        enteredPin = numberpad.getPin()
        del numberpad

        # Check to ensure the user has either set no password or one the correct length
        if (len(enteredPin) > 0) and (Settings.getPinLength() > len(enteredPin)):
            log("SetPin: Incorrect length pin entered, expecting %d digits" % Settings.getPinLength())
            xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001).encode('utf-8'), __addon__.getLocalizedString(32109).encode('utf-8'))
        else:
            # Now double check the value the user entered
            numberpad = NumberPad.createNumberPad(32107)
            numberpad.doModal()

            # Get the code that the user entered
            enteredPin2 = numberpad.getPin()
            del numberpad

            if enteredPin == enteredPin2:
                Settings.setPinValue(enteredPin)
            else:
                log("SetPin: Pin entry different, first: %s, second %s" % (enteredPin, enteredPin2))
                xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001).encode('utf-8'), __addon__.getLocalizedString(32108).encode('utf-8'))

    log("Stopping Pin Sentry Setter")
