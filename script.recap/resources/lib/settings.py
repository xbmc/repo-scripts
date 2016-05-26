# -*- coding: utf-8 -*-
import os
import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon(id='script.recap')
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
    @staticmethod
    def showOnContextMenu():
        return ADDON.getSetting("showOnContextMenu") == "true"

    @staticmethod
    def showPreviousOnContextMenu():
        return ADDON.getSetting("showPreviousOnContextMenu") == "true"

    @staticmethod
    def autoSelectSingle():
        return ADDON.getSetting("autoSelectSingle") == "true"

    @staticmethod
    def showImageCaptions():
        return ADDON.getSetting("showImageCaptions") == "true"

    @staticmethod
    def isLoopSlideshow():
        return ADDON.getSetting("loopSlideshow") == "true"

    @staticmethod
    def isAutoSlideshow():
        return ADDON.getSetting("autoSlideshow") == "true"

    @staticmethod
    def getAutoSlideshowInterval():
        interval = -1
        if Settings.isAutoSlideshow():
            # Seconds (float), Convert to milliseconds before returning
            interval = int(float(ADDON.getSetting("autoSlideshowInterval")) * 1000)
        return interval

    @staticmethod
    def getAutoSlideshowDelay():
        delay = 0
        if Settings.isAutoSlideshow():
            delay = int(float(ADDON.getSetting("autoSlideshowDelay")))
        return delay

    @staticmethod
    def getEmailAddress():
        email = ""
        if ADDON.getSetting("enableNotificationsForRequests") == "true":
            email = ADDON.getSetting("emailAddress")
        return email
