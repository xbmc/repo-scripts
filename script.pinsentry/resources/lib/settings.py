# -*- coding: utf-8 -*-
import os
import hashlib
import time
from datetime import date
import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon(id='script.pinsentry')
ADDON_ID = ADDON.getAddonInfo('id')


# Common logging module
def log(txt, loglevel=xbmc.LOGDEBUG):
    if (ADDON.getSetting("logEnabled") == "true") or (loglevel != xbmc.LOGDEBUG):
        if isinstance(txt, str):
            txt = txt.decode("utf-8")
        message = u'%s: %s' % (ADDON_ID, txt)
        xbmc.log(msg=message.encode("utf-8"), level=loglevel)


# There has been problems with calling join with non ascii characters,
# so we have this method to try and do the conversion for us
def os_path_join(dir, file):
    # Convert each argument - if an error, then it will use the default value
    # that was passed in
    try:
        dir = dir.decode("utf-8")
    except:
        pass
    try:
        file = file.decode("utf-8")
    except:
        pass
    return os.path.join(dir, file)


##############################
# Stores Various Settings
##############################
class Settings():
    INVALID_PIN_NOTIFICATION_POPUP = 0
    INVALID_PIN_NOTIFICATION_DIALOG = 1
    INVALID_PIN_NOTIFICATION_NONE = 2

    # Flags from www.pixabay.com User:OpenClipartVectors
    # https://pixabay.com/en/photos/?q=user%3AOpenClipartVectors+flag&image_type=&cat=&order=
    flags = [{'lang': 32301, 'icon': 'UK/UK-flag.png'},
             {'lang': 32302, 'icon': 'USA/USA-flag.png'},
             {'lang': 32303, 'icon': 'Germany/Germany-flag.png'},
             {'lang': 32304, 'icon': 'Ireland/Ireland-flag.png'},
             {'lang': 32305, 'icon': 'Netherlands/Netherlands-flag.png'},
             {'lang': 32306, 'icon': 'Australia/Australia-flag.png'},
             {'lang': 32307, 'icon': 'Brazil/Brazil-flag.png'},
             {'lang': 32308, 'icon': 'Hungary/Hungary-flag.png'},
             {'lang': 32309, 'icon': 'Denmark/Denmark-flag.png'},
             {'lang': 32310, 'icon': 'Norway/Norway-flag.png'},
             {'lang': 32311, 'icon': 'Sweden/Sweden-flag.png'},
             {'lang': 32312, 'icon': 'Finland/Finland-flag.png'},
             {'lang': 32313, 'icon': 'Canada/Canada-flag.png'},
             {'lang': 32315, 'icon': 'France/France-flag.png'}]

    # http://en.wikipedia.org/wiki/Motion_picture_rating_system
    movieCassificationsNames = [{'id': 1, 'name': '%s - U', 'lang': 32301, 'match': 'U', 'icon': 'UK/UK-U.png'},  # UK
                                {'id': 2, 'name': '%s - PG', 'lang': 32301, 'match': 'PG', 'icon': 'UK/UK-PG.png'},
                                {'id': 3, 'name': '%s - 12A', 'lang': 32301, 'match': '12A', 'icon': 'UK/UK-12A.png'},
                                {'id': 4, 'name': '%s - 12', 'lang': 32301, 'match': '12', 'icon': 'UK/UK-12.png'},
                                {'id': 5, 'name': '%s - 15', 'lang': 32301, 'match': '15', 'icon': 'UK/UK-15.png'},
                                {'id': 6, 'name': '%s - 18', 'lang': 32301, 'match': '18', 'icon': 'UK/UK-18.png'},
                                {'id': 7, 'name': '%s - R18', 'lang': 32301, 'match': 'R18', 'icon': 'UK/UK-R18.png'},
                                # USA
                                {'id': 8, 'name': '%s - G', 'lang': 32302, 'match': 'G', 'icon': 'USA/USA-G.png'},
                                {'id': 9, 'name': '%s - PG', 'lang': 32302, 'match': 'PG', 'icon': 'USA/USA-PG.png'},
                                {'id': 10, 'name': '%s - PG-13', 'lang': 32302, 'match': 'PG-13', 'icon': 'USA/USA-PG-13.png'},
                                {'id': 11, 'name': '%s - R', 'lang': 32302, 'match': 'R', 'icon': 'USA/USA-R.png'},
                                {'id': 12, 'name': '%s - NC-17', 'lang': 32302, 'match': 'NC-17', 'icon': 'USA/USA-NC-17.png'},
                                # Germany
                                {'id': 13, 'name': '%s - FSK 0', 'lang': 32303, 'match': '0', 'icon': 'Germany/Germany-FSK-0.png'},
                                {'id': 14, 'name': '%s - FSK 6', 'lang': 32303, 'match': '6', 'icon': 'Germany/Germany-FSK-6.png'},
                                {'id': 15, 'name': '%s - FSK 12', 'lang': 32303, 'match': '12', 'icon': 'Germany/Germany-FSK-12.png'},
                                {'id': 16, 'name': '%s - FSK 16', 'lang': 32303, 'match': '16', 'icon': 'Germany/Germany-FSK-16.png'},
                                {'id': 17, 'name': '%s - FSK 18', 'lang': 32303, 'match': '18', 'icon': 'Germany/Germany-FSK-18.png'},
                                # Ireland
                                {'id': 18, 'name': '%s - G', 'lang': 32304, 'match': 'G', 'icon': 'Ireland/Ireland-G.png'},
                                {'id': 19, 'name': '%s - PG', 'lang': 32304, 'match': 'PG', 'icon': 'Ireland/Ireland-PG.png'},
                                {'id': 20, 'name': '%s - 12A', 'lang': 32304, 'match': '12A', 'icon': 'Ireland/Ireland-12A.png'},
                                {'id': 21, 'name': '%s - 15A', 'lang': 32304, 'match': '15A', 'icon': 'Ireland/Ireland-15A.png'},
                                {'id': 22, 'name': '%s - 16', 'lang': 32304, 'match': '16', 'icon': 'Ireland/Ireland-16.png'},
                                {'id': 23, 'name': '%s - 18', 'lang': 32304, 'match': '18', 'icon': 'Ireland/Ireland-18.png'},
                                # Netherlands
                                {'id': 24, 'name': '%s - AL', 'lang': 32305, 'match': 'AL', 'icon': 'Netherlands/Netherlands-AL.png'},
                                {'id': 25, 'name': '%s - 6', 'lang': 32305, 'match': '6', 'icon': 'Netherlands/Netherlands-6.png'},
                                {'id': 26, 'name': '%s - 9', 'lang': 32305, 'match': '9', 'icon': 'Netherlands/Netherlands-9.png'},
                                {'id': 27, 'name': '%s - 12', 'lang': 32305, 'match': '12', 'icon': 'Netherlands/Netherlands-12.png'},
                                {'id': 28, 'name': '%s - 16', 'lang': 32305, 'match': '16', 'icon': 'Netherlands/Netherlands-16.png'},
                                # Australia
                                {'id': 29, 'name': '%s - E', 'lang': 32306, 'match': 'E', 'icon': 'Australia/Australia-E.png'},
                                {'id': 30, 'name': '%s - G', 'lang': 32306, 'match': 'G', 'icon': 'Australia/Australia-G.png'},
                                {'id': 31, 'name': '%s - PG', 'lang': 32306, 'match': 'PG', 'icon': 'Australia/Australia-PG.png'},
                                {'id': 32, 'name': '%s - M', 'lang': 32306, 'match': 'M', 'icon': 'Australia/Australia-M.png'},
                                {'id': 33, 'name': '%s - MA15+', 'lang': 32306, 'match': 'MA15+', 'icon': 'Australia/Australia-MA.png'},
                                {'id': 34, 'name': '%s - R18+', 'lang': 32306, 'match': 'R18+', 'icon': 'Australia/Australia-R.png'},
                                {'id': 35, 'name': '%s - X18+', 'lang': 32306, 'match': 'X18+', 'icon': 'Australia/Australia-X.png'},
                                # Brazil
                                {'id': 36, 'name': '%s - L', 'lang': 32307, 'match': 'L', 'icon': 'Brazil/Brazil-L.png'},
                                {'id': 37, 'name': '%s - 10', 'lang': 32307, 'match': '10', 'icon': 'Brazil/Brazil-10.png'},
                                {'id': 38, 'name': '%s - 12', 'lang': 32307, 'match': '12', 'icon': 'Brazil/Brazil-12.png'},
                                {'id': 39, 'name': '%s - 14', 'lang': 32307, 'match': '14', 'icon': 'Brazil/Brazil-14.png'},
                                {'id': 40, 'name': '%s - 16', 'lang': 32307, 'match': '16', 'icon': 'Brazil/Brazil-16.png'},
                                {'id': 41, 'name': '%s - 18', 'lang': 32307, 'match': '18', 'icon': 'Brazil/Brazil-18.png'},
                                # Hungary
                                {'id': 42, 'name': '%s - 0', 'lang': 32308, 'match': '0', 'icon': 'Hungary/Hungary-0.png'},
                                {'id': 43, 'name': '%s - 6', 'lang': 32308, 'match': '6', 'icon': 'Hungary/Hungary-6.png'},
                                {'id': 44, 'name': '%s - 12', 'lang': 32308, 'match': '12', 'icon': 'Hungary/Hungary-12.png'},
                                {'id': 45, 'name': '%s - 16', 'lang': 32308, 'match': '16', 'icon': 'Hungary/Hungary-16.png'},
                                {'id': 46, 'name': '%s - 18', 'lang': 32308, 'match': '18', 'icon': 'Hungary/Hungary-18.png'},
                                {'id': 47, 'name': '%s - X', 'lang': 32308, 'match': 'X', 'icon': 'Hungary/Hungary-X.png'},
                                # Denmark
                                {'id': 48, 'name': '%s - A', 'lang': 32309, 'match': 'A', 'icon': 'Denmark/Denmark-A.png'},
                                {'id': 49, 'name': '%s - 7', 'lang': 32309, 'match': '7', 'icon': 'Denmark/Denmark-7.png'},
                                {'id': 50, 'name': '%s - 11', 'lang': 32309, 'match': '11', 'icon': 'Denmark/Denmark-11.png'},
                                {'id': 51, 'name': '%s - 15', 'lang': 32309, 'match': '15', 'icon': 'Denmark/Denmark-15.png'},
                                {'id': 52, 'name': '%s - F', 'lang': 32309, 'match': 'F', 'icon': 'Denmark/Denmark-F.png'},
                                # Norway
                                {'id': 53, 'name': '%s - A', 'lang': 32310, 'match': 'A', 'icon': 'Norway/Norway-A.png'},
                                {'id': 54, 'name': '%s - 7', 'lang': 32310, 'match': '7', 'icon': 'Norway/Norway-7.png'},
                                {'id': 55, 'name': '%s - 11', 'lang': 32310, 'match': '11', 'icon': 'Norway/Norway-11.png'},
                                {'id': 56, 'name': '%s - 15', 'lang': 32310, 'match': '15', 'icon': 'Norway/Norway-15.png'},
                                {'id': 57, 'name': '%s - 18', 'lang': 32310, 'match': '18', 'icon': 'Norway/Norway-18.png'},
                                # Norway (New classifications for 2015 onwards)
                                {'id': 58, 'name': '%s - A', 'lang': 32310, 'match': 'A', 'icon': 'Norway/Norway-2015-A.png'},
                                {'id': 59, 'name': '%s - 6', 'lang': 32310, 'match': '6', 'icon': 'Norway/Norway-2015-6.png'},
                                {'id': 60, 'name': '%s - 9', 'lang': 32310, 'match': '9', 'icon': 'Norway/Norway-2015-9.png'},
                                {'id': 61, 'name': '%s - 12', 'lang': 32310, 'match': '12', 'icon': 'Norway/Norway-2015-12.png'},
                                {'id': 62, 'name': '%s - 15', 'lang': 32310, 'match': '15', 'icon': 'Norway/Norway-2015-15.png'},
                                {'id': 63, 'name': '%s - 18', 'lang': 32310, 'match': '18', 'icon': 'Norway/Norway-2015-18.png'},
                                # Sweden
                                {'id': 64, 'name': '%s - Btl', 'lang': 32311, 'match': 'Btl', 'icon': None},
                                {'id': 65, 'name': '%s - 7', 'lang': 32311, 'match': '7', 'icon': None},
                                {'id': 66, 'name': '%s - 11', 'lang': 32311, 'match': '11', 'icon': None},
                                {'id': 67, 'name': '%s - 15', 'lang': 32311, 'match': '15', 'icon': None},
                                # Finland
                                {'id': 68, 'name': '%s - S', 'lang': 32312, 'match': 'S', 'icon': 'Finland/Finland-S.png'},
                                {'id': 69, 'name': '%s - 7', 'lang': 32312, 'match': '7', 'icon': 'Finland/Finland-7.png'},
                                {'id': 69, 'name': '%s - 12', 'lang': 32312, 'match': '12', 'icon': 'Finland/Finland-12.png'},
                                {'id': 69, 'name': '%s - 16', 'lang': 32312, 'match': '16', 'icon': 'Finland/Finland-16.png'},
                                {'id': 69, 'name': '%s - 18', 'lang': 32312, 'match': '18', 'icon': 'Finland/Finland-18.png'},
                                # Canada
                                {'id': 70, 'name': '%s - G', 'lang': 32313, 'match': 'G', 'icon': 'Canada/Canada-G.png'},
                                {'id': 71, 'name': '%s - PG', 'lang': 32313, 'match': 'PG', 'icon': 'Canada/Canada-PG.png'},
                                {'id': 72, 'name': '%s - 14A', 'lang': 32313, 'match': '14A', 'icon': 'Canada/Canada-14A.png'},
                                {'id': 73, 'name': '%s - 18A', 'lang': 32313, 'match': '18A', 'icon': 'Canada/Canada-18A.png'},
                                {'id': 74, 'name': '%s - R', 'lang': 32313, 'match': 'R', 'icon': 'Canada/Canada-R.png'},
                                {'id': 75, 'name': '%%s (%s) - G' % ADDON.getLocalizedString(32314), 'lang': 32313, 'match': 'G', 'icon': 'Canada/Canada-Quebec-G.png'},
                                {'id': 76, 'name': '%%s (%s) - 13+' % ADDON.getLocalizedString(32314), 'lang': 32313, 'match': '13+', 'icon': 'Canada/Canada-Quebec-13.png'},
                                {'id': 77, 'name': '%%s (%s) - 16+' % ADDON.getLocalizedString(32314), 'lang': 32313, 'match': '16+', 'icon': 'Canada/Canada-Quebec-16.png'},
                                {'id': 78, 'name': '%%s (%s) - 18+' % ADDON.getLocalizedString(32314), 'lang': 32313, 'match': '18+', 'icon': 'Canada/Canada-Quebec-18.png'},
                                # France
                                {'id': 79, 'name': '%s - U', 'lang': 32315, 'match': 'U', 'icon': None},
                                {'id': 80, 'name': '%s - 12', 'lang': 32315, 'match': '12', 'icon': None},
                                {'id': 81, 'name': '%s - 16', 'lang': 32315, 'match': '16', 'icon': None},
                                {'id': 82, 'name': '%s - 18', 'lang': 32315, 'match': '18', 'icon': None}]

    # http://en.wikipedia.org/wiki/Television_content_rating_systems
    tvCassificationsNames = [{'id': 1, 'name': '%s - TV-Y', 'lang': 32302, 'match': 'TV-Y', 'icon': 'USA/USA-TV-Y.png'},  # USA
                             {'id': 2, 'name': '%s - TV-Y7', 'lang': 32302, 'match': 'TV-Y7', 'icon': 'USA/USA-TV-Y7.png'},
                             {'id': 3, 'name': '%s - TV-G', 'lang': 32302, 'match': 'TV-G', 'icon': 'USA/USA-TV-G.png'},
                             {'id': 4, 'name': '%s - TV-PG', 'lang': 32302, 'match': 'TV-PG', 'icon': 'USA/USA-TV-PG.png'},
                             {'id': 5, 'name': '%s - TV-14', 'lang': 32302, 'match': 'TV-14', 'icon': 'USA/USA-TV-14.png'},
                             {'id': 6, 'name': '%s - TV-MA', 'lang': 32302, 'match': 'TV-MA', 'icon': 'USA/USA-TV-MA.png'},
                             # Netherlands
                             {'id': 7, 'name': '%s - AL', 'lang': 32305, 'match': 'AL', 'icon': 'Netherlands/Netherlands-AL.png'},
                             {'id': 8, 'name': '%s - 6', 'lang': 32305, 'match': '6', 'icon': 'Netherlands/Netherlands-6.png'},
                             {'id': 9, 'name': '%s - 9', 'lang': 32305, 'match': '9', 'icon': 'Netherlands/Netherlands-9.png'},
                             {'id': 10, 'name': '%s - 12', 'lang': 32305, 'match': '12', 'icon': 'Netherlands/Netherlands-12.png'},
                             {'id': 11, 'name': '%s - 16', 'lang': 32305, 'match': '16', 'icon': 'Netherlands/Netherlands-16.png'},
                             # Australia
                             {'id': 12, 'name': '%s - P', 'lang': 32306, 'match': 'P', 'icon': 'Australia/Australia-TV-P.png'},
                             {'id': 13, 'name': '%s - C', 'lang': 32306, 'match': 'C', 'icon': 'Australia/Australia-TV-C.png'},
                             {'id': 14, 'name': '%s - G', 'lang': 32306, 'match': 'G', 'icon': 'Australia/Australia-TV-G.png'},
                             {'id': 15, 'name': '%s - PG', 'lang': 32306, 'match': 'PG', 'icon': 'Australia/Australia-TV-PG.png'},
                             {'id': 16, 'name': '%s - M', 'lang': 32306, 'match': 'M', 'icon': 'Australia/Australia-TV-M.png'},
                             {'id': 17, 'name': '%s - MA15+', 'lang': 32306, 'match': 'MA15+', 'icon': 'Australia/Australia-TV-MA.png'},
                             {'id': 18, 'name': '%s - AV15+', 'lang': 32306, 'match': 'AV15+', 'icon': 'Australia/Australia-TV-AV.png'},
                             {'id': 19, 'name': '%s - R18+', 'lang': 32306, 'match': 'R18+', 'icon': 'Australia/Australia-R.png'},
                             # Brazil
                             {'id': 20, 'name': '%s - L', 'lang': 32307, 'match': 'L', 'icon': 'Brazil/Brazil-L.png'},
                             {'id': 21, 'name': '%s - 10', 'lang': 32307, 'match': '10', 'icon': 'Brazil/Brazil-10.png'},
                             {'id': 22, 'name': '%s - 12', 'lang': 32307, 'match': '12', 'icon': 'Brazil/Brazil-12.png'},
                             {'id': 23, 'name': '%s - 14', 'lang': 32307, 'match': '14', 'icon': 'Brazil/Brazil-14.png'},
                             {'id': 24, 'name': '%s - 16', 'lang': 32307, 'match': '16', 'icon': 'Brazil/Brazil-16.png'},
                             {'id': 25, 'name': '%s - 18', 'lang': 32307, 'match': '18', 'icon': 'Brazil/Brazil-18.png'},
                             # Hungary
                             {'id': 26, 'name': '%s - 0', 'lang': 32308, 'match': '0', 'icon': 'Hungary/Hungary-TV-0.png'},
                             {'id': 27, 'name': '%s - 6', 'lang': 32308, 'match': '6', 'icon': 'Hungary/Hungary-TV-6.png'},
                             {'id': 28, 'name': '%s - 12', 'lang': 32308, 'match': '12', 'icon': 'Hungary/Hungary-TV-12.png'},
                             {'id': 29, 'name': '%s - 16', 'lang': 32308, 'match': '16', 'icon': 'Hungary/Hungary-TV-16.png'},
                             {'id': 30, 'name': '%s - 18', 'lang': 32308, 'match': '18', 'icon': 'Hungary/Hungary-TV-18.png'},
                             # Finland
                             {'id': 31, 'name': '%s - S', 'lang': 32312, 'match': 'S', 'icon': 'Finland/Finland-S.png'},
                             {'id': 32, 'name': '%s - 7', 'lang': 32312, 'match': '7', 'icon': 'Finland/Finland-7.png'},
                             {'id': 33, 'name': '%s - 12', 'lang': 32312, 'match': '12', 'icon': 'Finland/Finland-12.png'},
                             {'id': 34, 'name': '%s - 16', 'lang': 32312, 'match': '16', 'icon': 'Finland/Finland-16.png'},
                             {'id': 35, 'name': '%s - 18', 'lang': 32312, 'match': '18', 'icon': 'Finland/Finland-18.png'},
                             # Canada
                             {'id': 36, 'name': '%s - C', 'lang': 32313, 'match': 'C', 'icon': 'Canada/Canada-TV-C.png'},
                             {'id': 37, 'name': '%s - C8', 'lang': 32313, 'match': 'C8', 'icon': 'Canada/Canada-TV-C8.png'},
                             {'id': 38, 'name': '%s - G', 'lang': 32313, 'match': 'G', 'icon': 'Canada/Canada-TV-G.png'},
                             {'id': 39, 'name': '%s - PG', 'lang': 32313, 'match': 'PG', 'icon': 'Canada/Canada-TV-PG.png'},
                             {'id': 40, 'name': '%s - 14+', 'lang': 32313, 'match': '14+', 'icon': 'Canada/Canada-TV-14.png'},
                             {'id': 41, 'name': '%s - 18+', 'lang': 32313, 'match': '18+', 'icon': 'Canada/Canada-TV-18.png'},
                             {'id': 42, 'name': '%%s (%s) - G' % ADDON.getLocalizedString(32314), 'lang': 32313, 'match': 'G', 'icon': 'Canada/Canada-Quebec-G.png'},
                             {'id': 43, 'name': '%%s (%s) - 13+' % ADDON.getLocalizedString(32314), 'lang': 32313, 'match': '13+', 'icon': 'Canada/Canada-Quebec-13.png'},
                             {'id': 44, 'name': '%%s (%s) - 16+' % ADDON.getLocalizedString(32314), 'lang': 32313, 'match': '16+', 'icon': 'Canada/Canada-Quebec-16.png'},
                             {'id': 45, 'name': '%%s (%s) - 18+' % ADDON.getLocalizedString(32314), 'lang': 32313, 'match': '18+', 'icon': 'Canada/Canada-Quebec-18.png'},
                             # Finland
                             {'id': 46, 'name': '%s - 10', 'lang': 32315, 'match': '10', 'icon': 'France/France-TV-10.png'},
                             {'id': 47, 'name': '%s - 12', 'lang': 32315, 'match': '12', 'icon': 'France/France-TV-12.png'},
                             {'id': 48, 'name': '%s - 16', 'lang': 32315, 'match': '16', 'icon': 'France/France-TV-16.png'},
                             {'id': 49, 'name': '%s - 18', 'lang': 32315, 'match': '18', 'icon': 'France/France-TV-18.png'}]

    @staticmethod
    def reloadSettings():
        # Before loading the new settings save off the length of the pin
        # this means that if the length of the pin has changed and the actual
        # pin value has not, we can clear the pin value
        pinLength = Settings.getPinLength()
        pinValue = ADDON.getSetting("pinValue")

        # Force the reload of the settings to pick up any new values
        global ADDON
        ADDON = xbmcaddon.Addon(id='script.pinsentry')

        if Settings.isPinSet():
            if pinLength != Settings.getPinLength():
                if pinValue == ADDON.getSetting("pinValue"):
                    for i in range(1, 6):
                        Settings.setPinValue("", i)
                        userId = "user%dPin" % i
                        Settings.setUserPinValue("", userId)
                    # Display the warning in the settings
                    ADDON.setSetting("pinValueSet", "false")

    @staticmethod
    def setPinValue(newPin, pinLevel=1):
        encryptedPin = ""
        if len(newPin) > 0:
            # Before setting the pin, encrypt it
            encryptedPin = Settings.encryptPin(newPin)

        # The first pin value does not have a numeric value at the end of it's ID
        pinSettingsValue = "pinValue"
        if pinLevel > 1:
            pinSettingsValue = "%s%d" % (pinSettingsValue, pinLevel)
        ADDON.setSetting(pinSettingsValue, encryptedPin)

    @staticmethod
    def setUserPinValue(newPin, pinId):
        encryptedPin = ""
        pinSet = 'false'
        if len(newPin) > 0:
            # Before setting the pin, encrypt it
            encryptedPin = Settings.encryptPin(newPin)
            pinSet = 'true'

        ADDON.setSetting(pinId, encryptedPin)
        ADDON.setSetting("%sSet" % pinId, pinSet)

    @staticmethod
    def checkPinSettings():
        # Check all of the pin settings to see if they are set
        # If they are not, then we need to enable the warning

        # Check how many pins are being used
        numLevels = Settings.getNumberOfLevels()

        # Clear any of the pins that are not active
        clearPinNum = 5
        while numLevels < clearPinNum:
            log("SetPin: Clearing pin %d" % clearPinNum)
            Settings.setPinValue("", clearPinNum)
            clearPinNum = clearPinNum - 1

        # Now check the remaining pins to see if they are set
        allPinsSet = True
        pinCheck = 1
        while pinCheck <= numLevels:
            if not Settings.isPinSet(pinCheck):
                allPinsSet = False
                break
            pinCheck = pinCheck + 1

        if allPinsSet:
            # This is an internal fudge so that we can display a warning if the pin is not set
            ADDON.setSetting("pinValueSet", "true")
        else:
            ADDON.setSetting("pinValueSet", "false")

        # Now we need to tidy up the user limits values
        numUsers = Settings.getNumberOfLimitedUsers()
        clearUserPinNum = 5
        while numUsers < clearUserPinNum:
            log("SetPin: Clearing user pin %d" % clearUserPinNum)
            userId = "user%dPin" % clearUserPinNum
            userNameId = "%sName" % userId
            Settings.setUserPinValue("", userId)

            # Set the user name to the default language specific one
            userName = "%s %d" % (ADDON.getLocalizedString(32036), clearUserPinNum)
            ADDON.setSetting(userNameId, userName)
            clearUserPinNum = clearUserPinNum - 1
        # Also clear the unrestricted user if no user limit is being used
        if numUsers < 1:
            Settings.setUserPinValue("", "unrestrictedUserPin")

    @staticmethod
    def encryptPin(rawValue):
        return hashlib.sha256(rawValue).hexdigest()

    @staticmethod
    def isPinSet(pinLevel=1):
        pinSettingsValue = "pinValue"
        if pinLevel > 1:
            pinSettingsValue = "%s%d" % (pinSettingsValue, pinLevel)
        pinValue = ADDON.getSetting(pinSettingsValue)
        if pinValue not in [None, ""]:
            return True
        return False

    @staticmethod
    def getPinLength():
        return int(float(ADDON.getSetting('pinLength')))

    @staticmethod
    def isPinCorrect(inputPin, pinLevel=1):
        pinSettingsValue = "pinValue"
        if pinLevel > 1:
            pinSettingsValue = "%s%d" % (pinSettingsValue, pinLevel)
        # First encrypt the pin that has been passed in
        inputPinEncrypt = Settings.encryptPin(inputPin)
        if inputPinEncrypt == ADDON.getSetting(pinSettingsValue):
            return True
        return False

    @staticmethod
    def isUserPinCorrect(inputPin, pinId, blankIsCorrect=True):
        # Make sure if the pin has not been set we do not lock the user out
        storedPin = ADDON.getSetting(pinId)
        if storedPin in [None, ""]:
            # Check if we are treating blank as a match to everything
            if blankIsCorrect:
                return True
            else:
                return False

        # First encrypt the pin that has been passed in
        inputPinEncrypt = Settings.encryptPin(inputPin)
        if inputPinEncrypt == storedPin:
            return True
        return False

    @staticmethod
    def checkPinClash(newPin, pinLevel=1):
        # Check all the existing pins to make sure they are not the same
        pinCheck = Settings.getNumberOfLevels()
        while pinCheck > 0:
            if pinCheck != pinLevel:
                if Settings.isPinSet(pinCheck):
                    if Settings.isPinCorrect(newPin, pinCheck):
                        # Found a matching pin, so report a clash
                        return True
            pinCheck = pinCheck - 1
        return False

    @staticmethod
    def checkUserPinClash(newPin, pinId):
        numUsers = Settings.getNumberOfLimitedUsers()
        # Check all the existing pins to make sure they are not the same
        if (numUsers > 0) and (pinId != 'unrestrictedUserPin'):
            if Settings.isUserPinCorrect(newPin, 'unrestrictedUserPin', False):
                return True
        if (numUsers > 0) and (pinId != 'user1Pin'):
            if Settings.isUserPinCorrect(newPin, 'user1Pin', False):
                return True
        if (numUsers > 1) and (pinId != 'user2Pin'):
            if Settings.isUserPinCorrect(newPin, 'user2Pin', False):
                return True
        if (numUsers > 2) and (pinId != 'user3Pin'):
            if Settings.isUserPinCorrect(newPin, 'user3Pin', False):
                return True
        if (numUsers > 3) and (pinId != 'user4Pin'):
            if Settings.isUserPinCorrect(newPin, 'user4Pin', False):
                return True
        if (numUsers > 4) and (pinId != 'user5Pin'):
            if Settings.isUserPinCorrect(newPin, 'user5Pin', False):
                return True
        return False

    @staticmethod
    def getSecurityLevelForPin(inputPin):
        pinCheck = Settings.getNumberOfLevels()
        aPinSet = False
        while pinCheck > 0:
            if Settings.isPinSet(pinCheck):
                aPinSet = True
                if Settings.isPinCorrect(inputPin, pinCheck):
                    return pinCheck
            pinCheck = pinCheck - 1
        # If no pins are set allow full access
        if not aPinSet:
            return 5
        return -1

    @staticmethod
    def getUserForPin(inputPin):
        numUsers = Settings.getNumberOfLimitedUsers()
        # Check all the users to see if this pin matches any
        if numUsers > 0:
            if Settings.isUserPinCorrect(inputPin, 'unrestrictedUserPin'):
                return 'unrestrictedUserPin'
            if Settings.isUserPinCorrect(inputPin, 'user1Pin'):
                return 'user1Pin'
        if numUsers > 1:
            if Settings.isUserPinCorrect(inputPin, 'user2Pin'):
                return 'user2Pin'
        if numUsers > 2:
            if Settings.isUserPinCorrect(inputPin, 'user3Pin'):
                return 'user3Pin'
        if numUsers > 3:
            if Settings.isUserPinCorrect(inputPin, 'user4Pin'):
                return 'user4Pin'
        if numUsers > 4:
            if Settings.isUserPinCorrect(inputPin, 'user5Pin'):
                return 'user5Pin'
        return None

    @staticmethod
    def getInvalidPinNotificationType():
        return int(float(ADDON.getSetting('invalidPinNotificationType')))

    @staticmethod
    def isPinActive():
        # Check if the time restriction is enabled
        if ADDON.getSetting("timeRestrictionEnabled") != 'true':
            return True

        # Get the current time
        localTime = time.localtime()
        currentTime = (localTime.tm_hour * 60) + localTime.tm_min

        # Get the start time
        startTimeStr = ADDON.getSetting("startTime")
        startTimeSplit = startTimeStr.split(':')
        startTime = (int(startTimeSplit[0]) * 60) + int(startTimeSplit[1])
        if startTime > currentTime:
            log("Pin not active until %s (%d) currently %d" % (startTimeStr, startTime, currentTime))
            return False

        # Now check the end time
        endTimeStr = ADDON.getSetting("endTime")
        endTimeSplit = endTimeStr.split(':')
        endTime = (int(endTimeSplit[0]) * 60) + int(endTimeSplit[1])
        if endTime < currentTime:
            log("Pin not active after %s (%d) currently %d" % (endTimeStr, endTime, currentTime))
            return False

        log("Pin active between %s (%d) and %s (%d) currently %d" % (startTimeStr, startTime, endTimeStr, endTime, currentTime))
        return True

    @staticmethod
    def getPinCachingEnabledDuration():
        cacheDuration = 0
        cacheSelection = int(ADDON.getSetting("pinCachingStatus"))
        if cacheSelection == 0:
            # Cache is off
            cacheDuration = 0
        elif cacheSelection == 1:
            # Caching is on with no timeout
            cacheDuration = -1
        elif cacheSelection == 2:
            # Will time-out, so get the timeout time
            cacheDuration = int(float(ADDON.getSetting("pinCachingDuration")))

        return cacheDuration

    @staticmethod
    def isDirectionKeysAsPin():
        return ADDON.getSetting("directionKeysAsPin") == 'true'

    @staticmethod
    def isDisplayBackground():
        return ADDON.getSetting("background") != "0"

    @staticmethod
    def getBackgroundImage():
        selectIdx = ADDON.getSetting("background")
        if selectIdx == "2":
            # PinSentry Fanart file as the BackgroundBrowser
            return ADDON.getAddonInfo('fanart')
        elif selectIdx == "3":
            # Custom image selected, so return the value entered
            return ADDON.getSetting("backgroundImage")
        # If we reach here then there is no background image
        # or we want a black background
        return None

    @staticmethod
    def isActiveVideoPlaying():
        return ADDON.getSetting("activityVideoPlaying") == 'true'

    @staticmethod
    def isActiveNavigation():
        return ADDON.getSetting("activityNavigation") == 'true'

    @staticmethod
    def isActivePlugins():
        return ADDON.getSetting("activityPlugins") == 'true'

    @staticmethod
    def isActiveSystemSettings():
        return ADDON.getSetting("activitySystemSettings") == 'true'

    @staticmethod
    def isActiveFileSource():
        return ADDON.getSetting("activityFileSource") == 'true'

    @staticmethod
    def isActiveFileSourcePlaying():
        return ADDON.getSetting("activityFileSourceNavigationOnly") != 'true'

    @staticmethod
    def showSecurityLevelInPlugin():
        if Settings.getNumberOfLevels() < 2:
            return False
        return ADDON.getSetting("showSecurityInfo") == 'true'

    @staticmethod
    def isSupportedMovieClassification(classification):
        for classificationItem in Settings.movieCassificationsNames:
            if classification == classificationItem['match']:
                return True
        return False

    @staticmethod
    def isSupportedTvShowClassification(classification):
        for classificationItem in Settings.tvCassificationsNames:
            if classification == classificationItem['match']:
                return True
        return False

    @staticmethod
    def getDefaultMoviesWithoutClassification():
        securityValue = 0
        if ADDON.getSetting("defaultMoviesWithoutClassification") != '0':
            securityValue = 1
        return securityValue

    @staticmethod
    def getDefaultTvShowsWithoutClassification():
        securityValue = 0
        if ADDON.getSetting("defaultTvShowsWithoutClassification") != '0':
            securityValue = 1
        return securityValue

    @staticmethod
    def isHighlightClassificationUnprotectedVideos():
        return ADDON.getSetting("highlightClassificationUnprotectedVideos") == 'true'

    @staticmethod
    def isPromptForPinOnStartup():
        return ADDON.getSetting("promptForPinOnStartup") == 'true'

    @staticmethod
    def getNumberOfLevels():
        return int(ADDON.getSetting("numberOfLevels")) + 1

    @staticmethod
    def getSettingsSecurityLevel():
        # The security level required to change the settings is the highest pin with a value set
        pinCheck = Settings.getNumberOfLevels()
        while pinCheck > 0:
            if Settings.isPinSet(pinCheck):
                return pinCheck
            pinCheck = pinCheck - 1
        return -1

    @staticmethod
    def getNumberOfLimitedUsers():
        return int(ADDON.getSetting("numberOfLimitedUsers"))

    @staticmethod
    def getUserStartTime(userId):
        startTimeTag = "%sStartTime" % userId
        # Get the start time
        startTimeStr = ADDON.getSetting(startTimeTag)
        startTimeSplit = startTimeStr.split(':')
        startTime = (int(startTimeSplit[0]) * 60) + int(startTimeSplit[1])
        return (startTime, startTimeStr)

    @staticmethod
    def getUserEndTime(userId):
        endTimeTag = "%sEndTime" % userId
        # Get the end time
        endTimeStr = ADDON.getSetting(endTimeTag)
        endTimeSplit = endTimeStr.split(':')
        endTime = (int(endTimeSplit[0]) * 60) + int(endTimeSplit[1])
        return (endTime, endTimeStr)

    @staticmethod
    def getUserViewingLimit(userId):
        viewingLimitTag = "%sViewingLimit" % userId
        viewingLimit = int(ADDON.getSetting(viewingLimitTag))
        return viewingLimit

    @staticmethod
    def getUserViewingUsedTime(userId):
        lastLimitDataTag = "%sLastLimitData" % userId
        lastLimitData = ADDON.getSetting(lastLimitDataTag)

        # Check to see if the last date that viewing limit was set is still today
        todaysDate = date.today().strftime("%d/%m/%y")

        # If not from today, then we have not used any for this user
        if todaysDate != lastLimitData:
            return 0

        # Now check to see how much the user has already used today
        limitUsedTag = "%sLimitUsed" % userId
        limitUsed = ADDON.getSetting(limitUsedTag)

        if limitUsed in [None, ""]:
            return 0
        return int(limitUsed)

    @staticmethod
    def setUserViewingUsedTime(userId, usedViewingTime):
        # Store the date when we last viewed something
        todaysDate = date.today().strftime("%d/%m/%y")
        lastLimitDataTag = "%sLastLimitData" % userId
        ADDON.setSetting(lastLimitDataTag, todaysDate)

        # Now store the amount of time we have used
        limitUsedTag = "%sLimitUsed" % userId
        ADDON.setSetting(limitUsedTag, str(usedViewingTime))

    @staticmethod
    def getWarnExpiringTime():
        return int(float(ADDON.getSetting('warnExpiringTime')))

    @staticmethod
    def getUserName(userId):
        userNameTag = "%sName" % userId
        return ADDON.getSetting(userNameTag)
