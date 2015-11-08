# -*- coding: utf-8 -*-
import os
import xbmc
import xbmcaddon
import logging

__addon__ = xbmcaddon.Addon(id='script.sonos')
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


# Class used to supply Kodi logging to the soco scripts
class SocoLogging(logging.Handler):
    def emit(self, message):
        log(message.getMessage())

    @staticmethod
    def enable():
        # Only enable SoCo logging if Addon Logging is enabled
        if __addon__.getSetting("logEnabled") == "true":
            xbmcLogHandler = SocoLogging()
            logger = logging.getLogger('soco')
            logger.setLevel(logging.DEBUG)
            logger.addHandler(xbmcLogHandler)


##############################
# Stores Addon Settings
##############################
class Settings():
    @staticmethod
    def getIPAddress():
        return __addon__.getSetting("ipAddress")

    @staticmethod
    def setIPAddress(chosenIPAddress):
        # Set the selected item into the settings
        __addon__.setSetting("ipAddress", chosenIPAddress)

    @staticmethod
    def getZoneName():
        return __addon__.getSetting("zoneName")

    @staticmethod
    def setZoneName(chosenZoneName):
        # Set the selected item into the settings
        __addon__.setSetting("zoneName", chosenZoneName)

    @staticmethod
    def isAutoIpUpdateEnabled():
        return __addon__.getSetting("autoIPUpdate") == 'true'

    @staticmethod
    def isNotificationEnabled():
        return __addon__.getSetting("notifEnabled") == 'true'

    @staticmethod
    def getNotificationDisplayDuration():
        # Convert to milliseconds before returning
        return int(float(__addon__.getSetting("notifDisplayDuration"))) * 1000

    @staticmethod
    def getNotificationCheckFrequency():
        # Value set in seconds
        return int(float(__addon__.getSetting("notifCheckFrequency")))

    @staticmethod
    def stopNotifIfVideoPlaying():
        return __addon__.getSetting("notifNotIfVideoPlaying") == 'true'

    @staticmethod
    def stopNotifIfControllerShowing():
        return __addon__.getSetting("notifNotIfControllerShowing") == 'true'

    @staticmethod
    def useXbmcNotifDialog():
        return __addon__.getSetting("xbmcNotifDialog") == 'true'

    @staticmethod
    def getRefreshInterval():
        # Convert to milliseconds before returning
        return int(float(__addon__.getSetting("refreshInterval")) * 1000)

    @staticmethod
    def getAvoidDuplicateCommands():
        # Seconds (float)
        return float(__addon__.getSetting("avoidDuplicateCommands"))

    @staticmethod
    def getBatchSize():
        # Batch size to get items from the Sonos Speaker
        return int(float(__addon__.getSetting("batchSize")))

    @staticmethod
    def getMaxListEntries():
        # Maximum number of values to show in any plugin list
        return int(float(__addon__.getSetting("maxListEntries")))

    @staticmethod
    def useSkinIcons():
        return __addon__.getSetting("useSkinIcons") == 'true'

    @staticmethod
    def displayArtistInfo():
        return __addon__.getSetting("displayArtistInfo") == 'true'

    @staticmethod
    def getArtistInfoLayout():
        layoutId = int(float(__addon__.getSetting("artistInfoLayout")))
        # Settings are indexed at zero, so add one to match the Window XML
        layoutId = layoutId + 1
        return "script-sonos-artist-slideshow-%s.xml" % layoutId

    @staticmethod
    def isLyricsInfoLayout():
        layoutId = int(float(__addon__.getSetting("artistInfoLayout")))
        # The only lyrics screen is script-sonos-artist-slideshow-4.xml
        # Settings are indexed at zero, so add one to match the Window XML
        return layoutId == 3

    @staticmethod
    def fullScreenArtistSlideshow():
        if int(float(__addon__.getSetting("artistInfoLayout"))) != 1:
            return False
        return __addon__.getSetting("fullScreenArtistSlideshow") == 'true'

    @staticmethod
    def hideSonosLogo():
        return __addon__.getSetting("hideSonosLogo") == 'true'

    @staticmethod
    def linkAudioWithSonos():
        return __addon__.getSetting("linkAudioWithSonos") == 'true'

    @staticmethod
    def switchSonosToLineIn():
        return __addon__.getSetting("switchSonosToLineIn") == 'true'

    @staticmethod
    def switchSonosToLineInOnMediaStart():
        return __addon__.getSetting("switchSonosToLineInOnMediaStart") == 'true'

    @staticmethod
    def getVolumeChangeIncrements():
        # Maximum number of values to show in any plugin list
        return int(float(__addon__.getSetting("volumeChangeIncrements")))

    @staticmethod
    def autoPauseSonos():
        return __addon__.getSetting("autoPauseSonos") == 'true'

    @staticmethod
    def autoResumeSonos():
        return int(float(__addon__.getSetting("autoResumeSonos")))

    @staticmethod
    def autoLaunchControllerOnStartup():
        return __addon__.getSetting("autoLaunchControllerOnStartup") == 'true'
