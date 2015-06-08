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
    movieCassificationsNames = [{'id': 1, 'name': 'UK - U', 'match': 'U'},
                                {'id': 2, 'name': 'UK - PG', 'match': 'PG'},
                                {'id': 3, 'name': 'UK - 12A', 'match': '12A'},
                                {'id': 4, 'name': 'UK - 12', 'match': '12'},
                                {'id': 5, 'name': 'UK - 15', 'match': '15'},
                                {'id': 6, 'name': 'UK - 18', 'match': '18'},
                                {'id': 7, 'name': 'UK - R18', 'match': 'R18'},
                                {'id': 8, 'name': 'USA - G', 'match': 'G'},
                                {'id': 9, 'name': 'USA - PG', 'match': 'PG'},
                                {'id': 10, 'name': 'USA - PG-13', 'match': 'PG-13'},
                                {'id': 11, 'name': 'USA - R', 'match': 'R'},
                                {'id': 12, 'name': 'USA - NC-17', 'match': 'NC-17'}]

    # http://en.wikipedia.org/wiki/Television_content_rating_systems
    tvCassificationsNames = [{'id': 1, 'name': 'USA - TV-Y', 'match': 'TV-Y'},
                             {'id': 2, 'name': 'USA - TV-Y7', 'match': 'TV-Y7'},
                             {'id': 3, 'name': 'USA - TV-Y7-FV', 'match': 'TV-Y7-FV'},
                             {'id': 4, 'name': 'USA - TV-G', 'match': 'TV-G'},
                             {'id': 5, 'name': 'USA - TV-PG', 'match': 'TV-PG'},
                             {'id': 6, 'name': 'USA - TV-14', 'match': 'TV-14'},
                             {'id': 7, 'name': 'USA - TV-MA', 'match': 'TV-MA'}]

    @staticmethod
    def reloadSettings():
        # Force the reload of the settings to pick up any new values
        global __addon__
        __addon__ = xbmcaddon.Addon(id='script.pinsentry')

    @staticmethod
    def setPinValue(newPin):
        # Before setting the pin, encrypt it
        encryptedPin = Settings.encryptPin(newPin)
        __addon__.setSetting("pinValue", encryptedPin)
        if len(newPin) > 0:
            # This is an internal fudge so that we can display a warning if the pin is not set
            __addon__.setSetting("pinValueSet", "true")
        else:
            __addon__.setSetting("pinValueSet", "false")

    @staticmethod
    def encryptPin(rawValue):
        return hashlib.sha256(rawValue).hexdigest()

    @staticmethod
    def isPinSet():
        pinValue = __addon__.getSetting("pinValue")
        if pinValue not in [None, ""]:
            return True
        return False

    @staticmethod
    def getPinLength():
        return int(float(__addon__.getSetting('pinLength')))

    @staticmethod
    def isPinCorrect(inputPin):
        # First encrypt the pin that has been passed in
        inputPinEncrypt = Settings.encryptPin(inputPin)
        if inputPinEncrypt == __addon__.getSetting('pinValue'):
            return True
        return False

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
