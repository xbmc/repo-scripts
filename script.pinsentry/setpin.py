# -*- coding: utf-8 -*-
import sys
import xbmc
import xbmcaddon
import xbmcgui

# Import the common settings
from resources.lib.settings import log
from resources.lib.settings import Settings
from resources.lib.numberpad import NumberPad

ADDON = xbmcaddon.Addon(id='script.pinsentry')


# Function to set the pin
def setPin(pinLevel=1):
    okToChangePin = True

    # Check if the pin is already set, if it is, then we need to prompt for that first
    # before we allow the user to just change it
    if Settings.isPinSet(pinLevel):
        log("SetPin: Existing pin set, prompting for it")
        # Prompt the user for the pin
        numberpad = NumberPad.createNumberPad(32105)
        numberpad.doModal()

        # Get the code that the user entered
        enteredPin = numberpad.getPin()
        del numberpad

        if not Settings.isPinCorrect(enteredPin, pinLevel):
            log("SetPin: Incorrect Existing Pin Entered")
            okToChangePin = False
            xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001).encode('utf-8'), ADDON.getLocalizedString(32104).encode('utf-8'))
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
            xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001).encode('utf-8'), ADDON.getLocalizedString(32109).encode('utf-8'))
        elif Settings.checkPinClash(enteredPin, pinLevel):
            # This pin clashes with an existing pin
            log("SetPin: Entered pin clashes with an existing pin")
            xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001).encode('utf-8'), ADDON.getLocalizedString(32112).encode('utf-8'))
        else:
            # Now double check the value the user entered
            numberpad = NumberPad.createNumberPad(32107)
            numberpad.doModal()

            # Get the code that the user entered
            enteredPin2 = numberpad.getPin()
            del numberpad

            if enteredPin == enteredPin2:
                Settings.setPinValue(enteredPin, pinLevel)
            else:
                log("SetPin: Pin entry different, first: %s, second %s" % (enteredPin, enteredPin2))
                xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001).encode('utf-8'), ADDON.getLocalizedString(32108).encode('utf-8'))


# Function to set the user pin
def setUserPin(pinId):
    # Prompt the user for the pin
    numberpad = NumberPad.createNumberPad(32106)
    numberpad.doModal()

    # Get the code that the user entered
    enteredPin = numberpad.getPin()
    del numberpad

    # Check to ensure the user has either set no password or one the correct length
    if (len(enteredPin) > 0) and (Settings.getPinLength() > len(enteredPin)):
        log("SetPin: Incorrect length pin entered, expecting %d digits" % Settings.getPinLength())
        xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001).encode('utf-8'), ADDON.getLocalizedString(32109).encode('utf-8'))
    elif Settings.checkUserPinClash(enteredPin, pinId):
        # This pin clashes with an existing pin
        log("SetPin: Entered pin clashes with an existing pin")
        xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001).encode('utf-8'), ADDON.getLocalizedString(32112).encode('utf-8'))
    else:
        # Now double check the value the user entered
        numberpad = NumberPad.createNumberPad(32107)
        numberpad.doModal()

        # Get the code that the user entered
        enteredPin2 = numberpad.getPin()
        del numberpad

        if enteredPin == enteredPin2:
            Settings.setUserPinValue(enteredPin, pinId)
        else:
            log("SetPin: Pin entry different, first: %s, second %s" % (enteredPin, enteredPin2))
            xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001).encode('utf-8'), ADDON.getLocalizedString(32108).encode('utf-8'))


##################################
# Main of the PinSentry Setter
##################################
if __name__ == '__main__':
    log("Starting Pin Sentry Setter")

    # Before setting the pin we need to ensure that all dialog boxes are closed
    xbmc.executebuiltin("Dialog.Close(all, true)", True)

    numArgs = len(sys.argv)
    log("SetPin: Number of arguments %d" % numArgs)

    # If there are no arguments, then the pins are for default pin access per video
    if numArgs < 2:
        # Get the number of pins that have been set
        numLevels = Settings.getNumberOfLevels()
        log("SetPin: number of pins is %d" % numLevels)

        if numLevels < 2:
            # Only one pin to set
            setPin()
        else:
            # Need to prompt the user to see which pin they are trying to set
            displayNameList = []
            for i in range(1, numLevels + 1):
                notSetMsg = ""
                if not Settings.isPinSet(i):
                    notSetMsg = " %s" % ADDON.getLocalizedString(32024)

                displayString = "%s %d%s" % (ADDON.getLocalizedString(32021), i, notSetMsg)
                displayNameList.append(displayString)
            select = xbmcgui.Dialog().select(ADDON.getLocalizedString(32001), displayNameList)

            if select != -1:
                log("SetPin: Setting pin for %d" % (select + 1))
                setPin(select + 1)
    else:
        log("SetPin: Setting pin for %s" % sys.argv[1])
        setUserPin(sys.argv[1])

    # Tidy up any old pins and set any warnings
    Settings.checkPinSettings()
    log("Stopping Pin Sentry Setter")
