# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon(id='script.sleep')
ADDON_ID = ADDON.getAddonInfo('id')


# Common logging module
def log(txt, loglevel=xbmc.LOGDEBUG):
    if (ADDON.getSetting("logEnabled") == "true") or (loglevel != xbmc.LOGDEBUG):
        if isinstance(txt, str):
            txt = txt.decode("utf-8")
        message = u'%s: %s' % (ADDON_ID, txt)
        xbmc.log(msg=message.encode("utf-8"), level=loglevel)


##############################
# Stores Various Settings
##############################
class Settings():
    SHUTDOWN_DEFAULT = 0
    SHUTDOWN_HTTP = 1
    SHUTDOWN_SCREENSAVER = 2
    SHUTDOWN_SCRIPT = 3

    DIM_LEVEL = (
        '00000000',
        '11000000',
        '22000000',
        '33000000',
        '44000000',
        '55000000',
        '66000000',
        '77000000',
        '88000000',
        '99000000',
        'AA000000',
        'BB000000',
        'CC000000',
        'DD000000',
        'EE000000',
        'FF000000'
    )

    @staticmethod
    def reloadSettings():
        # Force the reload of the settings to pick up any new values
        global ADDON
        ADDON = xbmcaddon.Addon(id='script.sleep')

    @staticmethod
    def getIntervalLength():
        return int(float(ADDON.getSetting("intervalLength")))

    @staticmethod
    def getWarningLength():
        return int(float(ADDON.getSetting("warningLength")))

    @staticmethod
    def getMaxSleepTime():
        return int(float(ADDON.getSetting("maxSleepTime")))

    @staticmethod
    def pauseVideoForDialogDisplay():
        return ADDON.getSetting("pauseVideoForDialogDisplay") == 'true'

    @staticmethod
    def shutdownOnScreensaver():
        return ADDON.getSetting("shutdownOnScreensaver") == 'true'

    @staticmethod
    def displaySleepReminders():
        return ADDON.getSetting("displaySleepReminders") == 'true'

    @staticmethod
    def getDimValue():
        # The actual dim level (Hex) is one of
        # Where 00000000 is not changed
        # So that is a total of 16 different options
        # FF000000 would be completely black
        if ADDON.getSetting("dimLevel"):
            return Settings.DIM_LEVEL[int(ADDON.getSetting("dimLevel"))]
        else:
            return '00000000'

    @staticmethod
    def getShutdownCommand():
        return int(ADDON.getSetting("shutdownCommand"))

    @staticmethod
    def getShutdownURL():
        if Settings.getShutdownCommand() != Settings.SHUTDOWN_HTTP:
            return None
        return ADDON.getSetting("shutdownHttpLink")

    @staticmethod
    def getShutdownScript():
        if Settings.getShutdownCommand() != Settings.SHUTDOWN_SCRIPT:
            return None
        return ADDON.getSetting("shutdownScript")

    @staticmethod
    def getKeymapData():
        index = int(ADDON.getSetting("buttonSelection"))
        if index == 0:
            # No button mapping required
            return None

        # Need the keyboard and remote
        keyboard = []
        remote = []

        if index == 1:  # Mute
            keyboard.append({'name': 'volume_mute', 'ctrl': False, 'alt': False, 'shift': False, 'code': False})
            keyboard.append({'name': 'f8', 'ctrl': False, 'alt': False, 'shift': False, 'code': False})
            remote.append({'name': 'mute', 'ctrl': False, 'alt': False, 'shift': False, 'code': False})
        elif index == 2:  # Star
            keyboard.append({'name': 'eight', 'ctrl': True, 'alt': False, 'shift': True, 'code': False})
            keyboard.append({'name': 'eight', 'ctrl': False, 'alt': False, 'shift': True, 'code': False})
            remote.append({'name': 'star', 'ctrl': False, 'alt': False, 'shift': False, 'code': False})
        elif index == 3:  # Custom
            isCode = False
            if int(ADDON.getSetting("controlEntryType")) == 1:
                isCode = True
            # Check to see if there is a keyboard button value
            keyboardButton = ADDON.getSetting("keyboardName")
            if keyboardButton not in [None, ""]:
                alt = False
                ctrl = False
                shift = False
                if not isCode:
                    keyboardButton = Settings.checkForNumber(keyboardButton)
                    alt = ADDON.getSetting("keyboardAlt") == 'true'
                    ctrl = ADDON.getSetting("keyboardCtrl") == 'true'
                    shift = ADDON.getSetting("keyboardShift") == 'true'
                keyboard.append({'name': keyboardButton, 'ctrl': ctrl, 'alt': alt, 'shift': shift, 'code': isCode})
            remoteButton = ADDON.getSetting("remoteName")
            if remoteButton not in [None, ""]:
                if not isCode:
                    remoteButton = Settings.checkForNumber(remoteButton)
                remote.append({'name': remoteButton, 'ctrl': False, 'alt': False, 'shift': False, 'code': isCode})

        # Check for the case where both the keyboard and remote are not set
        if (len(keyboard) < 1) and (len(remote) < 1):
            return None

        # Now add our new mappings and return them
        keymapDetails = {'keyboard': keyboard, 'remote': remote}
        return keymapDetails

    @staticmethod
    def checkForNumber(srcText):
        newValue = srcText
        if srcText.startswith('0'):
            newValue = 'zero'
        elif srcText.startswith('1'):
            newValue = 'one'
        elif srcText.startswith('2'):
            newValue = 'two'
        elif srcText.startswith('3'):
            newValue = 'three'
        elif srcText.startswith('4'):
            newValue = 'four'
        elif srcText.startswith('5'):
            newValue = 'five'
        elif srcText.startswith('6'):
            newValue = 'six'
        elif srcText.startswith('7'):
            newValue = 'seven'
        elif srcText.startswith('8'):
            newValue = 'eight'
        elif srcText.startswith('9'):
            newValue = 'nine'
        return newValue

    @staticmethod
    def setKeymapData(buttonCode):
        # Make sure custom is enabled (it should already be
        if int(ADDON.getSetting("buttonSelection")) != 3:
            ADDON.setSetting("buttonSelection", str(3))
        # Make sure the Control type is set to "Code"
        if int(ADDON.getSetting("controlEntryType")) != 1:
            ADDON.setSetting("controlEntryType", str(1))
        # Switch it back to manual setup so the user can see it's got a value
        if ADDON.getSetting("automaticSetup") != 'false':
            ADDON.setSetting("automaticSetup", 'false')

        # Set the code for the button
        ADDON.setSetting("keyboardName", buttonCode)
        ADDON.setSetting("remoteName", buttonCode)
