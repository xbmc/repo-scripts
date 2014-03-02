# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon

__addon__     = xbmcaddon.Addon(id='script.sonos')
__addonid__   = __addon__.getAddonInfo('id')

# Load the Sonos controller component
from sonos import Sonos

# Import the Mock Sonos class for testing where there is no live Sonos system
from mocksonos import TestMockSonos

# Common logging module
def log(txt):
    if __addon__.getSetting( "logEnabled" ) == "true":
        if isinstance (txt,str):
            txt = txt.decode("utf-8")
        message = u'%s: %s' % (__addonid__, txt)
        xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)
        

##############################
# Stores Addon Settings
##############################
class Settings():

    @staticmethod
    def getSonosDevice(ipAddress=None):
        sonosDevice = None
        if Settings.useTestData():
            sonosDevice = TestMockSonos()
        else:
            if ipAddress == None:
                ipAddress = Settings.getIPAddress()
            if ipAddress != "0.0.0.0":
                sonosDevice = Sonos(ipAddress)
        log("Sonos: IP Address = %s" % ipAddress)
        return sonosDevice

    @staticmethod
    def getSonosDiscovery():
        return SonosDiscovery()

    @staticmethod
    def getIPAddress():
        return __addon__.getSetting("ipAddress")

    @staticmethod
    def setIPAddress(chosenIPAddress):
        # Set the selected item into the settings
        __addon__.setSetting("ipAddress", chosenIPAddress)

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
    def useXbmcNotifDialog():
        return __addon__.getSetting("xbmcNotifDialog") == 'true'

    @staticmethod
    def useTestData():
        return __addon__.getSetting("useTestData") == 'true'

    @staticmethod
    def getRefreshInterval():
        # Convert to milliseconds before returning
        return int(float(__addon__.getSetting("refreshInterval")) * 1000)

    @staticmethod
    def getBatchSize():
        # Batch size to get items from the Sonos Speaker
        return int(float(__addon__.getSetting("batchSize")))
