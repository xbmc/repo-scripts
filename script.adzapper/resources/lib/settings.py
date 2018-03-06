# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon(id='script.adzapper')
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

    @staticmethod
    def reloadSettings():
        # Force the reload of the settings to pick up any new values
        global ADDON
        ADDON = xbmcaddon.Addon(id='script.adzapper')

    @staticmethod
    def getIntervalLength():
        return int(float(ADDON.getSetting("intervalLength")))

    @staticmethod
    def getStartLength():
        return int(float(ADDON.getSetting("startLength")))    
    
    @staticmethod
    def getWarningLength():
        return int(float(ADDON.getSetting("warningLength")))

    @staticmethod
    def getMaxTimerLength():
        return int(float(ADDON.getSetting("maxTimerLength")))
