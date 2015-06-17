# -*- coding: utf-8 -*-
import os
import hashlib
import time
import xbmc
import xbmcaddon

__addon__ = xbmcaddon.Addon(id='script.pinsentry')
__addonid__ = __addon__.getAddonInfo('id')


# Common logging module
def log(txt, loglevel=xbmc.LOGDEBUG):
    if (__addon__.getSetting("logEnabled") == "true") or (loglevel != xbmc.LOGDEBUG):
        if isinstance(txt, str):
            txt = txt.decode("utf-8")
        message = u'%s: %s' % (__addonid__, txt)
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
                                {'id': 47, 'name': '%s - X', 'lang': 32308, 'match': 'X', 'icon': 'Hungary/Hungary-X.png'}]

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
                             {'id': 30, 'name': '%s - 18', 'lang': 32308, 'match': '18', 'icon': 'Hungary/Hungary-TV-18.png'}]

    @staticmethod
    def reloadSettings():
        # Force the reload of the settings to pick up any new values
        global __addon__
        __addon__ = xbmcaddon.Addon(id='script.pinsentry')

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
        __addon__.setSetting(pinSettingsValue, encryptedPin)

        # Flag if one of the pin numbers is not set
        allPinsSet = True
        if not Settings.isPinSet():
            allPinsSet = False
        else:
            # Check how many pins are being used
            numLevels = Settings.getNumberOfLevels()
            pinCheck = 2
            while pinCheck <= numLevels:
                if not Settings.isPinSet(pinCheck):
                    allPinsSet = False
                    break
                pinCheck = pinCheck + 1

        if allPinsSet:
            # This is an internal fudge so that we can display a warning if the pin is not set
            __addon__.setSetting("pinValueSet", "true")
        else:
            __addon__.setSetting("pinValueSet", "false")

    @staticmethod
    def encryptPin(rawValue):
        return hashlib.sha256(rawValue).hexdigest()

    @staticmethod
    def isPinSet(pinLevel=1):
        pinSettingsValue = "pinValue"
        if pinLevel > 1:
            pinSettingsValue = "%s%d" % (pinSettingsValue, pinLevel)
        pinValue = __addon__.getSetting(pinSettingsValue)
        if pinValue not in [None, ""]:
            return True
        return False

    @staticmethod
    def getPinLength():
        return int(float(__addon__.getSetting('pinLength')))

    @staticmethod
    def isPinCorrect(inputPin, pinLevel=1):
        pinSettingsValue = "pinValue"
        if pinLevel > 1:
            pinSettingsValue = "%s%d" % (pinSettingsValue, pinLevel)
        # First encrypt the pin that has been passed in
        inputPinEncrypt = Settings.encryptPin(inputPin)
        if inputPinEncrypt == __addon__.getSetting(pinSettingsValue):
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
    def getInvalidPinNotificationType():
        return int(float(__addon__.getSetting('invalidPinNotificationType')))

    @staticmethod
    def isPinActive():
        # Check if the time restriction is enabled
        if __addon__.getSetting("timeRestrictionEnabled") != 'true':
            return True

        # Get the current time
        localTime = time.localtime()
        currentTime = (localTime.tm_hour * 60) + localTime.tm_min

        # Get the start time
        startTimeStr = __addon__.getSetting("startTime")
        startTimeSplit = startTimeStr.split(':')
        startTime = (int(startTimeSplit[0]) * 60) + int(startTimeSplit[1])
        if startTime > currentTime:
            log("Pin not active until %s (%d) currently %d" % (startTimeStr, startTime, currentTime))
            return False

        # Now check the end time
        endTimeStr = __addon__.getSetting("endTime")
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
        cacheSelection = int(__addon__.getSetting("pinCachingStatus"))
        if cacheSelection == 0:
            # Cache is off
            cacheDuration = 0
        elif cacheSelection == 1:
            # Caching is on with no timeout
            cacheDuration = -1
        elif cacheSelection == 2:
            # Will time-out, so get the timeout time
            cacheDuration = int(float(__addon__.getSetting("pinCachingDuration")))

        return cacheDuration

    @staticmethod
    def isDirectionKeysAsPin():
        return __addon__.getSetting("directionKeysAsPin") == 'true'

    @staticmethod
    def isDisplayBackground():
        return __addon__.getSetting("background") != "0"

    @staticmethod
    def getBackgroundImage():
        selectIdx = __addon__.getSetting("background")
        if selectIdx == "2":
            # PinSentry Fanart file as the BackgroundBrowser
            return __addon__.getAddonInfo('fanart')
        elif selectIdx == "3":
            # Custom image selected, so return the value entered
            return __addon__.getSetting("backgroundImage")
        # If we reach here then there is no background image
        # or we want a black background
        return None

    @staticmethod
    def isActiveVideoPlaying():
        return __addon__.getSetting("activityVideoPlaying") == 'true'

    @staticmethod
    def isActiveNavigation():
        return __addon__.getSetting("activityNavigation") == 'true'

    @staticmethod
    def isActivePlugins():
        return __addon__.getSetting("activityPlugins") == 'true'

    @staticmethod
    def isActiveFileSource():
        return __addon__.getSetting("activityFileSource") == 'true'

    @staticmethod
    def isActiveFileSourcePlaying():
        return __addon__.getSetting("activityFileSourceNavigationOnly") != 'true'

    @staticmethod
    def showSecurityLevelInPlugin():
        if Settings.getNumberOfLevels() < 2:
            return False
        return __addon__.getSetting("showSecurityInfo") == 'true'

    @staticmethod
    def isSupportedMovieClassification(classification):
        for classification in Settings.movieCassificationsNames:
            if classification == classification['match']:
                return True
        return False

    @staticmethod
    def isSupportedTvShowClassification(classification):
        for classification in Settings.tvCassificationsNames:
            if classification == classification['match']:
                return True
        return False

    @staticmethod
    def getDefaultMoviesWithoutClassification():
        securityValue = 0
        if __addon__.getSetting("defaultMoviesWithoutClassification") != '0':
            securityValue = 1
        return securityValue

    @staticmethod
    def getDefaultTvShowsWithoutClassification():
        securityValue = 0
        if __addon__.getSetting("defaultTvShowsWithoutClassification") != '0':
            securityValue = 1
        return securityValue

    @staticmethod
    def isHighlightClassificationUnprotectedVideos():
        return __addon__.getSetting("highlightClassificationUnprotectedVideos") == 'true'

    @staticmethod
    def getNumberOfLevels():
        return int(__addon__.getSetting("numberOfLevels")) + 1

    @staticmethod
    def getSettingsSecurityLevel():
        # The security level required to change the settings is the highest pin with a value set
        pinCheck = Settings.getNumberOfLevels()
        while pinCheck > 0:
            if Settings.isPinSet(pinCheck):
                return pinCheck
            pinCheck = pinCheck - 1
        return -1
