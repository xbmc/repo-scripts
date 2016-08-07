# -*- coding: utf-8 -*-
import os
import xbmc
import xbmcaddon
import logging

ADDON = xbmcaddon.Addon(id='script.sonos')
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


# Class used to supply Kodi logging to the soco scripts
class SocoLogging(logging.Handler):
    def emit(self, message):
        log(message.getMessage())

    @staticmethod
    def enable():
        # Only enable SoCo logging if Addon Logging is enabled
        if ADDON.getSetting("logEnabled") == "true":
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
        return ADDON.getSetting("ipAddress")

    @staticmethod
    def setIPAddress(chosenIPAddress):
        # Set the selected item into the settings
        ADDON.setSetting("ipAddress", chosenIPAddress)

    @staticmethod
    def getZoneName():
        return ADDON.getSetting("zoneName")

    @staticmethod
    def setZoneName(chosenZoneName):
        # Set the selected item into the settings
        ADDON.setSetting("zoneName", chosenZoneName)

    @staticmethod
    def isAutoIpUpdateEnabled():
        return ADDON.getSetting("autoIPUpdate") == 'true'

    @staticmethod
    def isNotificationEnabled():
        return ADDON.getSetting("notifEnabled") == 'true'

    @staticmethod
    def getNotificationDisplayDuration():
        # Convert to milliseconds before returning
        return int(float(ADDON.getSetting("notifDisplayDuration"))) * 1000

    @staticmethod
    def getNotificationCheckFrequency():
        # Value set in seconds
        return int(float(ADDON.getSetting("notifCheckFrequency")))

    @staticmethod
    def stopNotifIfVideoPlaying():
        return ADDON.getSetting("notifNotIfVideoPlaying") == 'true'

    @staticmethod
    def stopNotifIfControllerShowing():
        return ADDON.getSetting("notifNotIfControllerShowing") == 'true'

    @staticmethod
    def useXbmcNotifDialog():
        return ADDON.getSetting("xbmcNotifDialog") == 'true'

    @staticmethod
    def getRefreshInterval():
        # Convert to milliseconds before returning
        return int(float(ADDON.getSetting("refreshInterval")) * 1000)

    @staticmethod
    def getAvoidDuplicateCommands():
        # Seconds (float)
        return float(ADDON.getSetting("avoidDuplicateCommands"))

    @staticmethod
    def getBatchSize():
        # Batch size to get items from the Sonos Speaker
        return int(float(ADDON.getSetting("batchSize")))

    @staticmethod
    def getMaxListEntries():
        # Maximum number of values to show in any plugin list
        return int(float(ADDON.getSetting("maxListEntries")))

    @staticmethod
    def useSkinIcons():
        return ADDON.getSetting("useSkinIcons") == 'true'

    @staticmethod
    def displayArtistInfo():
        return ADDON.getSetting("displayArtistInfo") == 'true'

    @staticmethod
    def getArtistInfoLayout():
        layoutId = int(float(ADDON.getSetting("artistInfoLayout")))
        # Settings are indexed at zero, so add one to match the Window XML
        layoutId = layoutId + 1
        return "script-sonos-artist-slideshow-%s.xml" % layoutId

    @staticmethod
    def isLyricsInfoLayout():
        layoutId = int(float(ADDON.getSetting("artistInfoLayout")))
        # The only lyrics screen is script-sonos-artist-slideshow-4.xml
        # Settings are indexed at zero, so add one to match the Window XML
        return layoutId == 3

    @staticmethod
    def fullScreenArtistSlideshow():
        if int(float(ADDON.getSetting("artistInfoLayout"))) != 1:
            return False
        return ADDON.getSetting("fullScreenArtistSlideshow") == 'true'

    @staticmethod
    def hideSonosLogo():
        return ADDON.getSetting("hideSonosLogo") == 'true'

    @staticmethod
    def linkAudioWithSonos():
        return ADDON.getSetting("linkAudioWithSonos") == 'true'

    @staticmethod
    def redirectVolumeControls():
        return ADDON.getSetting("redirectVolumeControls") == 'true'

    @staticmethod
    def switchSonosToLineIn():
        return ADDON.getSetting("switchSonosToLineIn") == 'true'

    @staticmethod
    def switchSonosToLineInOnMediaStart():
        return ADDON.getSetting("switchSonosToLineInOnMediaStart") == 'true'

    @staticmethod
    def getVolumeChangeIncrements():
        # Maximum number of values to show in any plugin list
        return int(float(ADDON.getSetting("volumeChangeIncrements")))

    @staticmethod
    def autoPauseSonos():
        return ADDON.getSetting("autoPauseSonos") == 'true'

    @staticmethod
    def autoResumeSonos():
        return int(float(ADDON.getSetting("autoResumeSonos")))

    @staticmethod
    def autoLaunchControllerOnStartup():
        return ADDON.getSetting("autoLaunchControllerOnStartup") == 'true'

    @staticmethod
    def getChecksPerSecond():
        return int(float(ADDON.getSetting("checksPerSecond")))
